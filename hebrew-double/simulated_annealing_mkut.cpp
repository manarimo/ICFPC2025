#include <cstdio>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>
#include <unordered_set>

using namespace std;

const int MAX_N = 90;
const int MAX_PLAN_LENGTH = MAX_N * 18;

class random {
    public:
    // [0, x)
    inline static unsigned get(unsigned x) {
        return ((unsigned long long)xorshift() * x) >> 32;
    }
    
    // [x, y]
    inline static unsigned get(unsigned x, unsigned y) {
        return get(y - x + 1) + x;
    }
    
    // [0, x] (x = 2^c - 1)
    inline static unsigned get_fast(unsigned x) {
        return xorshift() & x;
    }
    
    // [0.0, 1.0]
    inline static double probability() {
        return xorshift() * INV_MAX;
    }
    
    inline static bool toss() {
        return xorshift() & 1;
    }
    
    private:
    constexpr static double INV_MAX = 1.0 / 0xFFFFFFFF;
    
    inline static unsigned xorshift() {
        static unsigned x = 123456789, y = 362436039, z = 521288629, w = 88675123;
        unsigned t = x ^ (x << 11);
        x = y, y = z, z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
};

class timer {
    public:
    void start() {
        origin = chrono::system_clock::now();
    }
    
    inline double get_time() {
        return chrono::duration_cast<std::chrono::nanoseconds>(chrono::system_clock::now() - origin).count() * 1e-9;
    }
    
    private:
    chrono::system_clock::time_point origin;
};

class simulated_annealing {
    public:
    simulated_annealing();
    void init();
    inline bool end();
    inline bool accept(double current_score, double next_score);
    void print() const;
    
    private:
    constexpr static bool MAXIMIZE = false;
    constexpr static int LOG_SIZE = 0x10000;
    constexpr static int UPDATE_INTERVAL = 0xFFFF;
    constexpr static double TIME_LIMIT = 10;
    constexpr static double START_TEMP = 0.5;
    constexpr static double END_TEMP = 1e-9;
    constexpr static double TEMP_RATIO = (END_TEMP - START_TEMP) / TIME_LIMIT;
    double log_probability[LOG_SIZE];
    long long iteration = 0;
    long long accepted = 0;
    long long rejected = 0;
    double time = 0;
    double temp = START_TEMP;
    timer sa_timer;
};

simulated_annealing::simulated_annealing() {
    sa_timer.start();
    double inv = 1.0 / LOG_SIZE;
    for (int i = 0; i < LOG_SIZE; i++) log_probability[i] = log((i + 0.5) * inv);
    mt19937 engine;
    shuffle(log_probability, log_probability + LOG_SIZE, engine);
}

void simulated_annealing::init() {
    sa_timer.start();
    time = 0;
    temp = START_TEMP;
}

inline bool simulated_annealing::end() {
    iteration++;
    if ((iteration & UPDATE_INTERVAL) == 0) {
        time = sa_timer.get_time();
        temp = START_TEMP + TEMP_RATIO * time;
        return time >= TIME_LIMIT;
    } else {
        return false;
    }
}

inline bool simulated_annealing::accept(double current_score, double next_score) {
    double diff = (MAXIMIZE ? next_score - current_score : current_score - next_score);
    static unsigned short index = 0;
    if (diff >= 0 || diff > log_probability[index++] * temp) {
        accepted++;
        return true;
    } else {
        rejected++;
        return false;
    }
}

void simulated_annealing::print() const {
    fprintf(stderr, "iteration: %lld\n", iteration);
    fprintf(stderr, "accepted: %lld\n", accepted);
    fprintf(stderr, "rejected: %lld\n", rejected);
}

int n = 12;
int plans = 10;
int plan_length = n * 2 * 6;
const int MAX_P = 10;
int plan[MAX_P][MAX_PLAN_LENGTH];
int result[MAX_P][MAX_PLAN_LENGTH + 1];
int vertex[MAX_P][MAX_PLAN_LENGTH + 1];
int tmp_vertex[MAX_P][MAX_PLAN_LENGTH + 1];
int best_vertex[MAX_P][MAX_PLAN_LENGTH + 1];

int graph[MAX_N][6];
int cnt[MAX_N][6][MAX_N];
int cnt_sum[MAX_N][6];
int in_cnt[MAX_N][MAX_N];
int out_cnt[MAX_N][MAX_N];
int sum_cnt[MAX_N];
int cnt_diff[MAX_N][6][MAX_N];
int cnt_sum_diff[MAX_N][6];
int in_cnt_diff[MAX_N][MAX_N];
int out_cnt_diff[MAX_N][MAX_N];
int sum_cnt_diff[MAX_N];

struct door_t {
    int vertex, dir;
};
int encode_door(door_t door) {
    return door.vertex * 6 + door.dir;
}
door_t decode_door(int door) {
    return door_t{door / 6, door % 6};
}
struct edge_t {
    door_t door;
    int dest;
};
struct change_t {
    edge_t edge;
    int diff;
};
unordered_set<int> updated_verts_targets[MAX_N];
unordered_set<int> updated_verts;
unordered_set<int> updated_doors_targets[MAX_N][6];
unordered_set<int> updated_doors;
vector<pair<int,int>> current_bad;
vector<int> candidate[4];

int get_random(int bit) {
    return candidate[bit][random::get(candidate[bit].size())];
}

void update_current_bad() {
    current_bad.clear();

    for (int p = 0; p < plans; p++) {  
        for (int i = 0; i < plan_length; i++) {
            if (cnt[vertex[p][i]][plan[p][i]][vertex[p][i + 1]] != cnt_sum[vertex[p][i]][plan[p][i]]) {
                if (i > 0) current_bad.emplace_back(p, i);
                current_bad.emplace_back(p, i + 1);
            }
        }
    }

    for (int p = 0; p < plans; p++){
        for (int i = 0; i < plan_length; i++) {
            if (sum_cnt[vertex[p][i + 1]] > 6) {
                if (i > 0) current_bad.emplace_back(p, i);
                current_bad.emplace_back(p, i + 1);
            }
        }
    }
}

double init()
{
    double score = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            cnt_sum[i][j] = 0;
            for (int k = 0; k < n; k++) {
                cnt[i][j][k] = 0;
            }
        }
        for (int j = 0; j < n; j++) in_cnt[i][j] = out_cnt[i][j] = 0;
    }
    
    for (int p = 0; p < plans; p++) {  
        for (int i = 0; i < plan_length; i++) {
            cnt[vertex[p][i]][plan[p][i]][vertex[p][i + 1]]++;
            cnt_sum[vertex[p][i]][plan[p][i]]++;
        }
    }
    for (int p = 0; p < plans; p++) {  
        for (int i = 0; i < plan_length; i++) {
            if (cnt[vertex[p][i]][plan[p][i]][vertex[p][i + 1]] != cnt_sum[vertex[p][i]][plan[p][i]]) {
                if (i > 0) current_bad.emplace_back(p, i);
                current_bad.emplace_back(p, i + 1);
            }
        }
    }
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            for (int k = 0; k < n; k++) {
                score += cnt[i][j][k] * (cnt_sum[i][j] - cnt[i][j][k]) * 0.1;
            }
        }
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            for (int k = 0; k < n; k++) {
                if (cnt[i][j][k] > 0) {
                    in_cnt[k][i]++;
                    out_cnt[i][k]++;
                }
            }
        }
    }
    for (int i = 0; i < n; i++) {
        sum_cnt[i] = 0;
        for (int j = 0; j < n; j++) sum_cnt[i] += max(in_cnt[i][j], out_cnt[i][j]);
        score += max(0, sum_cnt[i] - 6);
    }
    for (int p = 0; p < plans; p++){
        for (int i = 0; i < plan_length; i++) {
            if (sum_cnt[vertex[p][i + 1]] > 6) {
                if (i > 0) current_bad.emplace_back(p, i);
                current_bad.emplace_back(p, i + 1);
            }
        }
    }

    update_current_bad();

    return score;
}

void build_graph()
{
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            graph[i][j] = -1;
            for (int k = 0; k < n; k++) {
                if (cnt[i][j][k] > 0) {
                    graph[i][j] = k;
                }
            }
        }
    }
}

double calc_door_score_diff(vector<change_t>& changes) {
    double score = 0;
    for (int door_i : updated_doors)
    {
        door_t door = decode_door(door_i);
        int sum_current = cnt_sum[door.vertex][door.dir];
        int sum_next = sum_current + cnt_sum_diff[door.vertex][door.dir];
        int cnt_rest = cnt_sum[door.vertex][door.dir];

        for (int dest : updated_doors_targets[door.vertex][door.dir])
        {
            int cnt_current = cnt[door.vertex][door.dir][dest];
            int cnt_next = cnt_current + cnt_diff[door.vertex][door.dir][dest];
            cnt_rest -= cnt_current;
            score += cnt_next * (sum_next - cnt_next) - cnt_current * (sum_current - cnt_current);
        }
        score += cnt_rest * (sum_next - cnt_rest) - cnt_rest * (sum_current - cnt_rest);
    }
    
    return score * 0.1;
}

double calc_capacity_score_diff(vector<change_t>& changes) {
    double score = 0;
    for (int x : updated_verts)
    {
        score += max(0, sum_cnt[x] + sum_cnt_diff[x] - 6) - max(0, sum_cnt[x] - 6);
    }
    
    return score;
}

void reset_diffs() {
    for (int door_i : updated_doors)
    {
        door_t door = decode_door(door_i);
        for (int dest : updated_doors_targets[door.vertex][door.dir])
        {
            cnt_diff[door.vertex][door.dir][dest] = 0;
        }
        cnt_sum_diff[door.vertex][door.dir] = 0;
        updated_doors_targets[door.vertex][door.dir].clear();
    }
    updated_doors.clear();

    for (int x : updated_verts)
    {
        for (int y : updated_verts_targets[x])
        {
            in_cnt_diff[x][y] = 0;
            out_cnt_diff[x][y] = 0;
        }
        sum_cnt_diff[x] = 0;
        updated_verts_targets[x].clear();
    }
    updated_verts.clear();
}

void calc_diffs(vector<change_t> changes) {
    reset_diffs();
    for (int i = 0; i < changes.size(); i++) {
        int vert = changes[i].edge.door.vertex;
        int dir = changes[i].edge.door.dir;
        int dest = changes[i].edge.dest;
        cnt_diff[vert][dir][dest] += changes[i].diff;
        cnt_sum_diff[vert][dir] += changes[i].diff;

        updated_doors.insert(encode_door(changes[i].edge.door));
        updated_doors_targets[vert][dir].insert(dest);
        updated_verts.insert(dest);
        updated_verts.insert(vert);
        updated_verts_targets[dest].insert(vert);
        updated_verts_targets[vert].insert(dest);
    }

    for (int x : updated_verts)
    {
        for (int y : updated_verts_targets[x])
        {
            for (int i = 0; i < 6; i++) {
                if (cnt[x][i][y] > 0) out_cnt_diff[x][y]--;
                if (cnt[x][i][y] + cnt_diff[x][i][y] > 0) out_cnt_diff[x][y]++;
                if (cnt[y][i][x] > 0) in_cnt_diff[x][y]--;
                if (cnt[y][i][x] + cnt_diff[y][i][x] > 0) in_cnt_diff[x][y]++;
            }
            sum_cnt_diff[x] += max(in_cnt[x][y] + in_cnt_diff[x][y], out_cnt[x][y] + out_cnt_diff[x][y])
                - max(in_cnt[x][y], out_cnt[x][y]);
        }
    }
}

void update_diffs() {
    for (int door_i : updated_doors)
    {
        door_t door = decode_door(door_i);
        int sum_current = cnt_sum[door.vertex][door.dir];
        int sum_next = sum_current + cnt_sum_diff[door.vertex][door.dir];
        int cnt_rest = cnt_sum[door.vertex][door.dir];
        for (int dest : updated_doors_targets[door.vertex][door.dir])
        {
            cnt[door.vertex][door.dir][dest] += cnt_diff[door.vertex][door.dir][dest];
        }
        cnt_sum[door.vertex][door.dir] += cnt_sum_diff[door.vertex][door.dir];
    }

    for (int x : updated_verts)
    {
        for (int y : updated_verts_targets[x])
        {
            in_cnt[x][y] += in_cnt_diff[x][y];
            out_cnt[x][y] += out_cnt_diff[x][y];
        }
        sum_cnt[x] += sum_cnt_diff[x];
    }

    update_current_bad();
}

void make_changes(int p, vector<int>& poss, int next, vector<change_t>& out) {
    for (int i = 0; i < poss.size(); i++) {
        int pos = poss[i];
        if (i == 0 || poss[i - 1] + 1 != pos) {
            door_t in_door{vertex[p][pos - 1], plan[p][pos - 1]};

            edge_t in_edge_current{in_door, vertex[p][pos]};
            edge_t in_edge_next{in_door, next};

            out.push_back(change_t{in_edge_current, -1});
            out.push_back(change_t{in_edge_next, 1});
        }

        if (pos < plan_length) {
            door_t out_door_current{vertex[p][pos], plan[p][pos]};
            door_t out_door_next{next, plan[p][pos]};

            int dest = i + 1 < poss.size() && poss[i + 1] == pos + 1 ? next : vertex[p][pos + 1];
            edge_t out_edge_current{out_door_current, vertex[p][pos + 1]};
            edge_t out_edge_next{out_door_next, dest};
            out.push_back(change_t{out_edge_current, -1});
            out.push_back(change_t{out_edge_next, 1});
        }
    }
}

double calc_score_diff(int p, vector<int>& poss, int next) {
    vector<change_t> changes;
    make_changes(p, poss, next, changes);
    calc_diffs(changes);

    double door_score_diff = calc_door_score_diff(changes);
    double capacity_score_diff = calc_capacity_score_diff(changes);
    
    return door_score_diff + capacity_score_diff;
}

int main() {
    scanf("%d", &n);
    plan_length = n * 2 * 6;
    scanf("%d", &plans);
    for (int p = 0; p < plans; ++p) {
        for (int i = 0; i < plan_length; i++) {
            scanf("%1d", &plan[p][i]);
        }
    }
    for (int p = 0; p < plans; ++p) {
        for (int i = 0; i <= plan_length; i++) {
            scanf("%1d", &result[p][i]);
        }
    }

    /*
    for (int p = 0; p < plans; ++p) {
        fprintf(stderr, "plan %d:\n", p);
        for (int i = 0; i <= plan_length; i++) {
            fprintf(stderr, "%d %d\n", plan[p][i], result[p][i]);
        }
        fputs("\n", stderr);
    }
    */
    
    int init_len = n;
    for (int i = 0; i < n; i++) candidate[i % 4].push_back(i);
    for (int p = 0; p < plans; ++p)
        for (int i = 1; i <= plan_length; i++) vertex[p][i] = best_vertex[p][i] = get_random(result[p][i]);

    double current_score = init(), best_score = current_score;
    simulated_annealing sa;
    printf("start : %f\n", current_score);
    unsigned short update = 0;
    for (int loop = 0; loop < 5 && current_score > 0; loop++) {
        sa.init();
        while (!sa.end() && current_score > 0) {
            update++;
            if (update == 0) {
                 for (int p = 0; p < plans; p++)
                    for (int i = 0; i <= plan_length; i++) vertex[p][i] = best_vertex[p][i];
                int pos = random::get(1, plan_length - init_len);
                for (int p = 0; p < plans; p++)
                    for (int i = pos; i <= pos + init_len; i++) vertex[p][i] = get_random(result[p][i]);
                current_score = init();
            }
            
            if (random::get(100) < 95) {
                int p, pos;
                if (random::get(100) < 30) {
                    auto pair = current_bad[random::get(current_bad.size())];
                    p = pair.first;
                    pos = pair.second;
                } else {
                    p = random::get(plans);
                    pos = random::get(plan_length) + 1;
                }
                int now = vertex[p][pos], next = get_random(result[p][pos]);
                if (now == next) continue;
                vector<int> poss;
                poss.push_back(pos);
                double next_score = current_score + calc_score_diff(p, poss, next);
                if (sa.accept(current_score, next_score)) {
                    vertex[p][pos] = next;
                    update_diffs();
                    current_score = next_score;
                    /*
                    int real_next_score = init();
                    if (next_score != real_next_score) {
                        fprintf(stderr, "A err %d %d\n", next_score, real_next_score);
                    } else {
                        // fprintf(stderr, "A ok %d %d\n", next_score, real_next_score);
                    }
                    */
                }
            } else {
                int p = random::get(plans);
                int pos = random::get(plan_length);
                int from = vertex[p][pos], edge = plan[p][pos], to = vertex[p][pos + 1];
                vector<int> poss;
                for (int i = 0; i < plan_length; i++) {
                    if (vertex[p][i] == from && plan[p][i] == edge && vertex[p][i + 1] % 4 == to % 4 && vertex[p][i + 1] != to) {
                        poss.push_back(i + 1);
                    }        
                }

                double next_score = current_score + calc_score_diff(p, poss, to);
                if (sa.accept(current_score, next_score)) {
                    for (int pos : poss) {
                        vertex[p][pos] = to;
                    }
                    update_diffs();
                    current_score = next_score;
                    /*
                    int real_next_score = init();
                    if (next_score != real_next_score) {
                        fprintf(stderr, "B err %d %d\n", next_score, real_next_score);
                    } else {
                        // fprintf(stderr, "B ok %d %d\n", next_score, real_next_score);
                    }
                    */
                }
            }
            
            if (current_score < best_score) {
                update = 0;
                best_score = current_score;
                for (int p = 0; p < plans; p++)
                    for (int i = 0; i <= plan_length; i++) best_vertex[p][i] = vertex[p][i];
                fprintf(stderr, "now : %f\n", best_score);
                // fflush(stderr);
            }
        }
    }
    printf("end : %f\n", current_score);
    sa.print();
    if (current_score > 0) return 0;
    
    build_graph();
    vector<vector<int>> parent(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) parent[graph[i][j]].push_back(i);
        }
    }
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] == -1) continue;
            vector<int>::iterator it = find(parent[i].begin(), parent[i].end(), graph[i][j]);
            if (it != parent[i].end()) parent[i].erase(it);
        }
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) continue;
            if (!parent[i].empty()) {
                graph[i][j] = parent[i].back();
                parent[i].pop_back();
            } else {
                graph[i][j] = i;
            }
        }
    }
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) printf("%d ", graph[i][j]);
    }
    puts("");
    puts("solved");
    
    return 0;
}
