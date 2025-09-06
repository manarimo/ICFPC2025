Wrapper Tool (stdin/stdout → HTTP proxy)

Overview

- Reads commands from stdin using the custom text protocol in `io-spec.txt` (not raw JSON).
- Proxies to the API server at `API_BASE`.
- Output format:
  - `explore`: plain text, one line per result list: `<len> v1 v2 ... vN`.
  - other endpoints: raw JSON from the server.
- On parsing/network errors, prints a small JSON error to stdout.

Environment

- `API_BASE` must be set, e.g. `http://localhost:8080`.

Build & Run (named pipes)

```
cd wrapper
go build -o wrapper
mkfifo /tmp/wrap_in /tmp/wrap_out
API_BASE=http://localhost:8080 ./wrapper /tmp/wrap_in /tmp/wrap_out

# In another terminal, write commands to /tmp/wrap_in and read replies from /tmp/wrap_out
# Example using shell redirection:
#   (printf "select\nTEAM-123\nprobatio\n"; sleep 1) > /tmp/wrap_in &
#   cat /tmp/wrap_out
```

Input Protocol (from `io-spec.txt`)

- Select
  - Lines:
    1) `select`
    2) `<team_id>`
    3) `<problem_name>`

- Explore
  - Lines:
    1) `explore`
    2) `<team_id>`
    3) `<N>` (number of plans)
    4..) `<plan_i>` repeated N times

- Guess
  - Lines:
    1) `guess`
    2) `<team_id>`
    3) `<label_1> <label_2> ... <label_K>` (space-separated integers)
    4) `<starting_room>` (integer)
    5) `<N>` (number of connections)
    6..) `<room_from> <door_from> <room_to> <door_to>` repeated N times

Server Payloads

- The wrapper converts inputs to server JSON per `api-spec.txt`:
  - `POST /select`: `{ "id", "problemName" }`
  - `POST /explore`: `{ "id", "plans" }`
  - `POST /guess`: `{ "id", "map": { "rooms", "startingRoom", "connections" } }`
  - `startingRoom` comes from the `<starting_room>` line in the guess input.

Notes

- Communication uses two FIFOs: the first arg is read-only (commands to wrapper), the second is write-only (responses from wrapper).
- The wrapper exits when the writer on the input FIFO closes (EOF). Run it under a supervisor if you want respawn behavior.
- Blank lines are ignored only where the protocol does not expect them; malformed or truncated input results in a JSON error.
- For `explore`, success responses are converted to plain text lines; non-2xx responses are forwarded as-is.
