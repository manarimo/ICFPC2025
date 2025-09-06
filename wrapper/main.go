package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type endpoint struct {
	Path string
}

var endpoints = map[string]endpoint{
	"select":  {Path: "/select"},
	"explore": {Path: "/explore"},
	"guess":   {Path: "/guess"},
}

// Wire types for API JSON
type selectReq struct {
	ID          string `json:"id"`
	ProblemName string `json:"problemName"`
}

type exploreReq struct {
	ID    string   `json:"id"`
	Plans []string `json:"plans"`
}

type connEnd struct {
	Room int `json:"room"`
	Door int `json:"door"`
}
type connection struct {
	From connEnd `json:"from"`
	To   connEnd `json:"to"`
}
type guessMap struct {
	Rooms        []int        `json:"rooms"`
	StartingRoom int          `json:"startingRoom"`
	Connections  []connection `json:"connections"`
}
type guessReq struct {
	ID  string   `json:"id"`
	Map guessMap `json:"map"`
}

func main() {
	base := strings.TrimSpace(os.Getenv("API_BASE"))
	if base == "" {
		fmt.Fprintln(os.Stderr, "ERROR: API_BASE environment variable is not set")
		os.Exit(2)
	}
	base = strings.TrimRight(base, "/")

	// Expect two arguments: input FIFO path and output FIFO path
	if len(os.Args) != 3 {
		prog := filepath.Base(os.Args[0])
		fmt.Fprintf(os.Stderr, "Usage: %s <in_fifo> <out_fifo>\n", prog)
		os.Exit(2)
	}
	inFIFO := os.Args[1]
	outFIFO := os.Args[2]

	// Open FIFOs once (exit on EOF)
	inFile, err := os.OpenFile(inFIFO, os.O_RDONLY, 0)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: open in fifo: %v\n", err)
		os.Exit(1)
	}
	defer inFile.Close()

	outFile, err := os.OpenFile(outFIFO, os.O_WRONLY, 0)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: open out fifo: %v\n", err)
		os.Exit(1)
	}
	defer outFile.Close()

	out := bufio.NewWriter(outFile)

	client := &http.Client{Timeout: 30 * time.Second}

	in := bufio.NewScanner(inFile)
	// Increase max token size to handle large payloads (16MB)
	in.Buffer(make([]byte, 64*1024), 16*1024*1024)

	for {
		if !in.Scan() {
			if err := in.Err(); err != nil && err != io.EOF {
				emitError(out, fmt.Errorf("reading input: %w", err))
				_ = out.Flush()
			}
			continue
		}
		line := strings.TrimSpace(in.Text())
		if line == "" {
			continue
		}

		cmd := line
		ep, ok := endpoints[cmd]
		if !ok {
			emitJSON(out, map[string]any{
				"error":    "unknown endpoint",
				"endpoint": cmd,
				"known":    keys(endpoints),
			})
			_ = out.Flush()
			continue
		}

		// Parse according to io-spec.txt to construct JSON body
		var bodyBytes []byte
		var pErr error
		switch cmd {
		case "select":
			bodyBytes, pErr = parseSelect(in)
		case "explore":
			bodyBytes, pErr = parseExplore(in)
		case "guess":
			bodyBytes, pErr = parseGuess(in)
		default:
			pErr = fmt.Errorf("unsupported command: %s", cmd)
		}
		if pErr != nil {
			emitError(out, pErr)
			_ = out.Flush()
			continue
		}

		// Build request
		url := base + ep.Path
		req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(bodyBytes))
		if err != nil {
			emitError(out, fmt.Errorf("creating request: %w", err))
			_ = out.Flush()
			continue
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Accept", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			emitError(out, fmt.Errorf("performing request: %w", err))
			_ = out.Flush()
			continue
		}

		respBody, readErr := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		if readErr != nil {
			emitError(out, fmt.Errorf("reading response: %w", readErr))
			_ = out.Flush()
			continue
		}

		// If non-2xx, still forward body; if body empty, synthesize an error JSON
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			if len(bytes.TrimSpace(respBody)) == 0 {
				emitJSON(out, map[string]any{
					"error":       "http_error",
					"status":      resp.StatusCode,
					"status_text": resp.Status,
				})
				_ = out.Flush()
				continue
			}
			// Forward non-2xx body as-is
			if _, err := out.Write(respBody); err != nil {
				emitError(out, fmt.Errorf("writing output: %w", err))
				_ = out.Flush()
				continue
			}
			if len(respBody) == 0 || respBody[len(respBody)-1] != '\n' {
				_, _ = out.WriteString("\n")
			}
			_ = out.Flush()
			continue
		}

		// Success responses: for explore, convert to plain text lines; otherwise forward body
		if cmd == "explore" {
			var ex struct {
				Results    [][]int `json:"results"`
				QueryCount int     `json:"queryCount"`
			}
			if err := json.Unmarshal(respBody, &ex); err != nil {
				// If parsing fails, forward raw body as a fallback
				if _, werr := out.Write(respBody); werr != nil {
					emitError(out, fmt.Errorf("writing output: %w", werr))
					_ = out.Flush()
					continue
				}
				if len(respBody) == 0 || respBody[len(respBody)-1] != '\n' {
					_, _ = out.WriteString("\n")
				}
				_ = out.Flush()
				continue
			}

			// Emit one line per result list: "<len> v1 v2 ... vN\n"
			for _, arr := range ex.Results {
				// Write length
				_, _ = out.WriteString(strconv.Itoa(len(arr)))
				for _, v := range arr {
					_, _ = out.WriteString(" ")
					_, _ = out.WriteString(strconv.Itoa(v))
				}
				_, _ = out.WriteString("\n")
			}
			_ = out.Flush()
			continue
		}

		// Default: forward raw response body
		if _, err := out.Write(respBody); err != nil {
			emitError(out, fmt.Errorf("writing output: %w", err))
			_ = out.Flush()
			continue
		}
		if len(respBody) == 0 || respBody[len(respBody)-1] != '\n' {
			_, _ = out.WriteString("\n")
		}
		_ = out.Flush()
	}
}

// no openOut helper in this version

func readRequiredLine(sc *bufio.Scanner) (string, error) {
	if !sc.Scan() {
		if err := sc.Err(); err != nil && err != io.EOF {
			return "", err
		}
		return "", fmt.Errorf("unexpected EOF while reading input")
	}
	return strings.TrimSpace(sc.Text()), nil
}

func parseSelect(sc *bufio.Scanner) ([]byte, error) {
	id, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("select: %w", err)
	}
	prob, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("select: %w", err)
	}
	req := selectReq{ID: id, ProblemName: prob}
	return json.Marshal(req)
}

func parseExplore(sc *bufio.Scanner) ([]byte, error) {
	id, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("explore: %w", err)
	}
	nLine, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("explore: %w", err)
	}
	n, err := strconv.Atoi(strings.TrimSpace(nLine))
	if err != nil || n < 0 {
		return nil, fmt.Errorf("explore: invalid count: %q", nLine)
	}
	plans := make([]string, 0, n)
	for i := 0; i < n; i++ {
		p, err := readRequiredLine(sc)
		if err != nil {
			return nil, fmt.Errorf("explore: plan %d: %w", i+1, err)
		}
		plans = append(plans, p)
	}
	req := exploreReq{ID: id, Plans: plans}
	return json.Marshal(req)
}

func parseGuess(sc *bufio.Scanner) ([]byte, error) {
	id, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("guess: %w", err)
	}
	labelsLine, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("guess: %w", err)
	}
	labelFields := strings.Fields(labelsLine)
	if len(labelFields) == 0 {
		return nil, fmt.Errorf("guess: no room labels provided")
	}
	rooms := make([]int, 0, len(labelFields))
	for i, f := range labelFields {
		v, convErr := strconv.Atoi(f)
		if convErr != nil {
			return nil, fmt.Errorf("guess: invalid label at pos %d: %q", i+1, f)
		}
		rooms = append(rooms, v)
	}

	startLine, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("guess: %w", err)
	}
	startingRoom, err := strconv.Atoi(strings.TrimSpace(startLine))
	if err != nil {
		return nil, fmt.Errorf("guess: invalid starting_room: %q", startLine)
	}

	nLine, err := readRequiredLine(sc)
	if err != nil {
		return nil, fmt.Errorf("guess: %w", err)
	}
	n, err := strconv.Atoi(strings.TrimSpace(nLine))
	if err != nil || n < 0 {
		return nil, fmt.Errorf("guess: invalid edges count: %q", nLine)
	}
	conns := make([]connection, 0, n)
	for i := 0; i < n; i++ {
		line, err := readRequiredLine(sc)
		if err != nil {
			return nil, fmt.Errorf("guess: edge %d: %w", i+1, err)
		}
		parts := strings.Fields(line)
		if len(parts) != 4 {
			return nil, fmt.Errorf("guess: edge %d: expected 4 integers, got %d", i+1, len(parts))
		}
		rf, err1 := strconv.Atoi(parts[0])
		df, err2 := strconv.Atoi(parts[1])
		rt, err3 := strconv.Atoi(parts[2])
		dt, err4 := strconv.Atoi(parts[3])
		if err1 != nil || err2 != nil || err3 != nil || err4 != nil {
			return nil, fmt.Errorf("guess: edge %d: invalid integers", i+1)
		}
		conns = append(conns, connection{From: connEnd{Room: rf, Door: df}, To: connEnd{Room: rt, Door: dt}})
	}
	req := guessReq{ID: id, Map: guessMap{Rooms: rooms, StartingRoom: startingRoom, Connections: conns}}
	return json.Marshal(req)
}

func emitError(out *bufio.Writer, err error) {
	emitJSON(out, map[string]any{"error": err.Error()})
}

func emitJSON(out *bufio.Writer, v any) {
	enc := json.NewEncoder(out)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
}

func keys(m map[string]endpoint) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}
