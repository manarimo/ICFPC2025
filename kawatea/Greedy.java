import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.collect.ImmutableMap;

import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class Greedy {
    private static final String API_URL = "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com/";
    private static final String ID = "xxx";
    private static final java.util.Map<Integer, String> PROBLEM_NAMES = ImmutableMap.of(
            3, "probatio",
            6, "primus",
            12, "secundus",
            18, "tertius",
            24, "quartus",
            30, "quintus"
    );
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final int MAX_N = 30;
    private static final int CHECK_NUM = 1;
    private static final int CHECK_LEN = 20;
    private static final String[] CHECK_STR = new String[6];
    private static final int[] LABEL = new int[MAX_N];
    private static final String[] ROUTE = new String[MAX_N];
    private static final int[][] GRAPH = new int[MAX_N][6];
    private static final List<List<List<Integer>>> NEIGHBORS = new ArrayList<>();

    public static class Select {
        public final String id;
        public final String problemName;

        Select(final String id, final String problemName) {
            this.id = id;
            this.problemName = problemName;
        }
    }

    public static class Explore {
        public final String id;
        public final List<String> plans;

        Explore(final String id, final List<String> plans) {
            this.id = id;
            this.plans = plans;
        }
    }

    public static class Edge {
        public final int room;
        public final int door;

        Edge(final int room, final int door) {
            this.room = room;
            this.door = door;
        }
    }

    public static class Edges {
        public final Edge from;
        public final Edge to;

        Edges(final Edge from, final Edge to) {
            this.from = from;
            this.to = to;
        }
    }

    public static class Map {
        public final List<Integer> rooms;
        public final int startingRoom;
        public final List<Edges> connections;

        Map(final List<Integer> rooms, final int startingRoom, final List<Edges> connections) {
            this.rooms = rooms;
            this.startingRoom = startingRoom;
            this.connections = connections;
        }
    }

    public static class Guess {

        public final String id;
        public final Map map;

        Guess(final String id, final Map map) {
            this.id = id;
            this.map = map;
        }
    }

    private static void select(final int n) {
        System.out.println("select");
        try {
            final URL url = new URL(API_URL + "select");
            final HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoInput(true);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.connect();

            final Select select = new Select(ID, PROBLEM_NAMES.get(n));
            final OutputStreamWriter os = new OutputStreamWriter(conn.getOutputStream());
            os.write(OBJECT_MAPPER.writeValueAsString(select));
            os.close();

            final JsonNode jsonNode = OBJECT_MAPPER.readTree(conn.getInputStream());
            System.out.println(jsonNode.get("problemName").asText());
        } catch (final Exception e) {
            throw new RuntimeException(e);
        }
    }

    static int explore_count = 0;

    private static List<List<Integer>> explore(final List<String> plans) {
        explore_count++;
        System.out.println("explore " + explore_count);
        try {
            final URL url = new URL(API_URL + "explore");
            final HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoInput(true);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.connect();

            final Explore explore = new Explore(ID, plans);
            System.out.println(OBJECT_MAPPER.writeValueAsString(explore));
            final OutputStreamWriter os = new OutputStreamWriter(conn.getOutputStream());
            os.write(OBJECT_MAPPER.writeValueAsString(explore));
            os.close();

            final List<List<Integer>> results = new ArrayList<>();
            final JsonNode jsonNode = OBJECT_MAPPER.readTree(conn.getInputStream());
            System.out.println(jsonNode.toString());
            for (final JsonNode res : jsonNode.get("results")) {
                final List<Integer> labels = new ArrayList<>();
                for (final JsonNode label : res) labels.add(label.asInt());
                results.add(labels);
            }
            return results;
        } catch (final Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static boolean guess(final Map map) {
        System.out.println("guess");
        try {
            final URL url = new URL(API_URL + "guess");
            final HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoInput(true);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.connect();

            final Guess guess = new Guess(ID, map);
            System.out.println(OBJECT_MAPPER.writeValueAsString(guess));
            final OutputStreamWriter os = new OutputStreamWriter(conn.getOutputStream());
            os.write(OBJECT_MAPPER.writeValueAsString(guess));
            os.close();

            final JsonNode jsonNode = OBJECT_MAPPER.readTree(conn.getInputStream());
            return jsonNode.get("correct").asBoolean();
        } catch (final Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static void init(final int n) {
        final Random random = new Random();
        for (int i = 0; i < CHECK_NUM; i++) {
            CHECK_STR[i] = String.valueOf(i);
            for (int j = 1; j < CHECK_LEN; j++) CHECK_STR[i] += String.valueOf(random.nextInt(6));
        }

        for (int i = 0; i < n; i++) LABEL[i] = -1;
        for (int i = 0; i < n; i++) ROUTE[i] = "";
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < 6; j++) GRAPH[i][j] = -1;
        }
        for (int i = 0; i < n; i++) NEIGHBORS.clear();

        LABEL[0] = 0;
        ROUTE[0] = "";
        final List<String> plans = new ArrayList<>();
        for (int i = 0; i < CHECK_NUM; i++) plans.add(CHECK_STR[i]);
        NEIGHBORS.add(explore(plans));
    }

    private static int get_index(final int label, final List<List<Integer>> neighbors) {
        for (int i = 0; i < NEIGHBORS.size(); i++) {
            if (LABEL[i] == label && NEIGHBORS.get(i).equals(neighbors)) return i;
        }
        return -1;
    }

    private static boolean solve(final int n) {
        select(n);
        init(n);

        int last = 1;
        for (int i = 0; i < n; i++) {
            final List<String> plans = new ArrayList<>();
            for (int j = 0; j < 6; j++) {
                for (int k = 0; k < CHECK_NUM; k++) plans.add(ROUTE[i] + j + CHECK_STR[k]);
            }
            final List<List<Integer>> results = explore(plans);
            final List<Integer> labels = new ArrayList<>();
            for (int j = 0; j < 6; j++) labels.add(results.get(j * CHECK_NUM).get(ROUTE[i].length() + 1));
            for (int j = 0; j < results.size(); j++)
                results.set(j, results.get(j).subList(ROUTE[i].length() + 1, results.get(j).size()));
            for (int j = 0; j < 6; j++) {
                int index = get_index(labels.get(j), results.subList(j * CHECK_NUM, (j + 1) * CHECK_NUM));
                if (index == -1) {
                    index = last++;
                    LABEL[index] = labels.get(j);
                    ROUTE[index] = ROUTE[i] + j;
                    NEIGHBORS.add(results.subList(j * CHECK_NUM, (j + 1) * CHECK_NUM));
                }
                GRAPH[i][j] = index;
            }
        }

        final List<Integer> rooms = new ArrayList<>();
        for (int i = 0; i < n; i++) rooms.add(LABEL[i]);
        final List<Edges> connections = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < 6; j++) {
                int c = 1;
                for (int k = 0; k < j; k++) {
                    if (GRAPH[i][j] == GRAPH[i][k]) c++;
                }
                for (int k = 0; k < 6; k++) {
                    if (GRAPH[GRAPH[i][j]][k] == i) c--;
                    if (c == 0) {
                        connections.add(new Edges(new Edge(i, j), new Edge(GRAPH[i][j], k)));
                        break;
                    }
                }
            }
        }
        final Map map = new Map(rooms, 0, connections);
        return guess(map);
    }

    public static void main(final String[] args) {
        final int n = 30;
        while (true) {
            try {
                final boolean correct = solve(n);
                if (correct) break;
            } catch (final Exception e) {
                System.out.println(e);
            }
        }
    }
}
