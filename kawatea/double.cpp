#include <cstdio>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

const int MAX_N = 60;
const int MAX_P = 10;
const int N_MUL = 6;

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
    void init_temp(double temp);
    void init();
    inline bool end();
    inline bool accept(double current_score, double next_score);
    void print() const;
    
    private:
    constexpr static bool MAXIMIZE = false;
    constexpr static int LOG_SIZE = 0x10000;
    constexpr static int UPDATE_INTERVAL = 0xFFFF;
    constexpr static double TIME_LIMIT = 10;
    double START_TEMP = 0.5;
    constexpr static double END_TEMP = 1e-9;
    double TEMP_RATIO = (END_TEMP - START_TEMP) / TIME_LIMIT;
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

void simulated_annealing::init_temp(double temp) {
    START_TEMP = temp;
    TEMP_RATIO = (END_TEMP - START_TEMP) / TIME_LIMIT;
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

int n = 30, nn;
int plans = 1;
int change_start = -1;
char tmp[MAX_N * N_MUL * 4 + 1];
int plan[MAX_P][MAX_N * N_MUL];
int change[MAX_P][MAX_N * N_MUL];
int result[MAX_P][MAX_N * N_MUL + 1];
int vertex[MAX_P][MAX_N * N_MUL + 1];
int tmp_vertex[MAX_P][MAX_N * N_MUL + 1];
int best_vertex[MAX_P][MAX_N * N_MUL + 1];
int graph[MAX_N][6];
int final_graph[MAX_N][6];
bool flip[MAX_N][6];
bool best_flip[MAX_N][6];
int edge_cnt[MAX_N][6][MAX_N];
int in_cnt[MAX_N][MAX_N][2];
int out_cnt[MAX_N][MAX_N][2];
int sum_cnt[MAX_N];
int label[MAX_N][2];
vector<int> candidate[4];

int get_random(int bit) {
    return candidate[bit][random::get(candidate[bit].size())];
}

int calc_score(vector<pair<int, int>>& bad) {
    bad.clear();
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            graph[i][j] = -1;
            for (int k = 0; k < nn; k++) edge_cnt[i][j][k] = 0;
        }
        for (int j = 0; j < nn; j++) in_cnt[i][j][0] = in_cnt[i][j][1] = out_cnt[i][j][0] = out_cnt[i][j][1] = 0;
    }
    
    int score = 0;
    for (int p = 0; p < plans; p++) {        
        for (int i = 0; i < n * N_MUL; i++) {
            edge_cnt[vertex[p][i]][plan[p][i]][vertex[p][i + 1]]++;
        }
    }
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            int best = 0, next_v;
            for (int k = 0; k < nn; k++) {
                if (edge_cnt[i][j][k] > best) {
                    best = edge_cnt[i][j][k];
                    next_v = k;
                }
            }
            if (best > 0) graph[i][j] = next_v;
        }
    }
    for (int p = 0; p < plans; p++) {        
        for (int i = 0; i < n * N_MUL; i++) {
            if (graph[vertex[p][i]][plan[p][i]] != vertex[p][i + 1]) {
                if (i > 0) bad.emplace_back(p, i);
                bad.emplace_back(p, i + 1);
                score++;
            }
        }
    }
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) {
                in_cnt[graph[i][j]][i][flip[i][j]]++;
                out_cnt[i][graph[i][j]][flip[i][j]]++;
            }
        }
    }
    for (int i = 0; i < nn; i++) {
        sum_cnt[i] = 0;
        for (int j = 0; j < nn; j++) {
            sum_cnt[i] += max(in_cnt[i][j][0], out_cnt[i][j][0]);
            sum_cnt[i] += max(in_cnt[i][j][1], out_cnt[i][j][1]);
        }
        if (sum_cnt[i] > 6) score += (sum_cnt[i] - 6);
    }
    for (int p = 0; p < plans; p++){
        for (int i = 0; i < n * N_MUL; i++) {
            if (sum_cnt[vertex[p][i + 1]] > 6) {
                if (i > 0) bad.emplace_back(p, i);
                bad.emplace_back(p, i + 1);
            }
        }
    }
    for (int p = 0; p < plans; p++) {
        int now = 0;
        for (int i = 0; i < nn; i++) {
            for (int j = 0; j < 2; j++) label[i][j] = i % 4;
        }
        for (int i = 0; i < n * N_MUL; i++) {
            if (change[p][i] != -1) label[vertex[p][i]][now] = change[p][i];
            if (flip[vertex[p][i]][plan[p][i]]) now = 1 - now;
            if (label[vertex[p][i + 1]][now] != result[p][i + 1]) {
                if (i > 0) bad.emplace_back(p, i);
                bad.emplace_back(p, i + 1);
                score++;
            }
        }
    }
    return score;
}

int main() {
    double temp;
    scanf("%d", &n);
    scanf("%d", &plans);
    scanf("%lf", &temp);
    for (int p = 0; p < plans; ++p) {
        scanf("%s", tmp);
        for (int i = 0, j = 0; i < n * N_MUL; i++, j++) {
            if (tmp[j] == '[') {
                change[p][i] = tmp[j + 1] - '0';
                j += 3;
                if (change_start == -1) change_start = i;
            } else {
                change[p][i] = -1;
            }
            plan[p][i] = tmp[j] - '0';
        }
    }
    for (int p = 0; p < plans; ++p) {
        scanf("%s", tmp);
        for (int i = 0, j = 0; i <= n * N_MUL; i++, j++) {
            result[p][i] = tmp[j] - '0';
            if (i < n * N_MUL && change[p][i] != -1) j++;
        }
    }
    
    nn = n / 2;
    int init_len = nn;
    for (int i = 0; i < nn; i++) candidate[i % 4].push_back(i);
    for (int p = 0; p < plans; ++p) {
        for (int i = 1; i <= n * N_MUL; i++) {
            if (i <= change_start) {
                vertex[p][i] = best_vertex[p][i] = get_random(result[p][i]);
            } else {
                vertex[p][i] = best_vertex[p][i] = random::get(nn);
            }
        }
    }
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) flip[i][j] = random::toss();
    }
    vector<pair<int, int>> current_bad, next_bad, best_bad;
    int current_score = calc_score(current_bad), best_score = current_score, last_score = current_score;
    simulated_annealing sa;
    sa.init_temp(temp);
    printf("start : %d\n", current_score);
    unsigned short update = 0;
    for (int loop = 0; loop < 1 && current_score > 0; loop++) {
        sa.init();
        while (!sa.end() && current_score > 0) {
            update++;
            if (update == 0) {
                current_score = best_score;
                current_bad = best_bad;
                for (int p = 0; p < plans; p++) {
                    for (int i = 0; i <= n * N_MUL; i++) vertex[p][i] = best_vertex[p][i];
                }
                for (int i = 0; i < nn; i++) {
                    for (int j = 0; j < 6; j++) flip[i][j] = best_flip[i][j];
                }
                int p = random::get(plans);
                int pos = random::get(1, n * N_MUL - init_len);
                for (int i = pos; i <= pos + init_len; i++) {
                    if (i <= change_start) {
                        vertex[p][i] = get_random(result[p][i]);
                    } else {
                        vertex[p][i] = random::get(nn);
                    }
                }
                current_score = calc_score(current_bad);
            }
            
            int select = random::get(100);
            if (select < 50) {
                int p, pos;
                if (random::get(100) < 25) {
                    auto pair = current_bad[random::get(current_bad.size())];
                    p = pair.first;
                    pos = pair.second;
                } else {
                    p = random::get(plans);
                    pos = random::get(1, n * N_MUL);
                }
                int now = vertex[p][pos], next;
                if (pos <= change_start) {
                    next = get_random(result[p][pos]);
                } else {
                    next = random::get(nn);
                }
                if (now == next) continue;
                vertex[p][pos] = next;
                int next_score = calc_score(next_bad);
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                    current_bad.swap(next_bad);
                } else {
                    vertex[p][pos] = now;
                }
            } else if (select < 99) {
                int x = random::get(nn), y = random::get(6);
                flip[x][y] = !flip[x][y];
                int next_score = calc_score(next_bad);
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                    current_bad.swap(next_bad);
                } else {
                    flip[x][y] = !flip[x][y];
                }
            } else {
                int p = random::get(plans);
                int pos = random::get(change_start);
                int from = vertex[p][pos], edge = plan[p][pos], to = vertex[p][pos + 1];
                for (int pp = 0; pp < plans; pp++) {
                    for (int i = 0; i <= n * N_MUL; i++) tmp_vertex[pp][i] = vertex[pp][i];
                    for (int i = 0; i < n * N_MUL; i++) {
                        if (vertex[pp][i] == from && plan[pp][i] == edge && (i + 1 > change_start || vertex[pp][i + 1] % 4 == to % 4)) vertex[pp][i + 1] = to;
                    }
                }
                int next_score = calc_score(next_bad);
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                    current_bad.swap(next_bad);
                } else {
                    for (int pp = 0; pp < plans; pp++) {
                        for (int i = 0; i <= n * N_MUL; i++) vertex[pp][i] = tmp_vertex[pp][i];
                    }
                }
            }
            
            if (current_score < best_score) {
                update = 0;
                best_score = current_score;
                best_bad = current_bad;
                for (int p = 0; p < plans; p++) {
                    for (int i = 0; i <= n * N_MUL; i++) best_vertex[p][i] = vertex[p][i];
                }
                for (int i = 0; i < nn; i++) {
                    for (int j = 0; j < 6; j++) best_flip[i][j] = flip[i][j];
                }
                /*
                if (current_score < 50 || last_score - current_score > 10) {
                    last_score = current_score;
                    fprintf(stderr, "now : %d\n", last_score);
                    fflush(stderr);
                }
                */
            }
        }
    }
    printf("end : %d\n", current_score);
    sa.print();
    if (current_score > 0) return 0;
    
    int estimate = 0;
    vector<vector<pair<int, int>>> parent(nn);
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) {
                parent[graph[i][j]].emplace_back(i, flip[i][j]);
            }
        }
    }
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] == -1) continue;
            vector<pair<int, int>>::iterator it = find(parent[i].begin(), parent[i].end(), make_pair(graph[i][j], (int)flip[i][j]));
            if (it != parent[i].end()) parent[i].erase(it);
        }
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) continue;
            if (!parent[i].empty()) {
                if (parent[i].size() > 1) estimate++;
                graph[i][j] = parent[i].back().first;
                flip[i][j] = parent[i].back().second;
                parent[i].pop_back();
            } else {
                estimate++;
                graph[i][j] = i;
                flip[i][j] = false;
            }
        }
    }
    
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (flip[i][j]) {
                final_graph[i][j] = graph[i][j] + nn;
                final_graph[i + nn][j] = graph[i][j];
            } else {
                final_graph[i][j] = graph[i][j];
                final_graph[i + nn][j] = graph[i][j] + nn;
            }
        }
    }
    
    printf("%d\n", estimate);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) printf("%d ", final_graph[i][j]);
    }
    puts("");
    puts("solved");
    
    return 0;
}
