#include <cstdio>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>
#include "score.h"
#include "globals.h"

using namespace std;


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
    constexpr static double TIME_LIMIT = 15;
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

// simulated_annealing.cppでのみ使用するグローバル変数
static vector<int> candidate[4];

int get_random(int bit) {
    return candidate[bit][random::get(candidate[bit].size())];
}


int main() {
    scanf("%d", &n);
    scanf("%d", &plans);
    for (int p = 0; p < plans; ++p) {
        for (int i = 0; i < n * N_MUL; i++) {
            scanf("%1d", &plan[p][i]);
        }
    }
    for (int p = 0; p < plans; ++p)
        for (int i = 0; i <= n * N_MUL; i++) scanf("%1d", &result[p][i]);
    
    int init_len = n;
    for (int i = 0; i < n; i++) candidate[i % 4].push_back(i);
    for (int p = 0; p < plans; ++p)
        for (int i = 1; i <= n * N_MUL; i++) vertex[p][i] = best_vertex[p][i] = get_random(result[p][i]);
    vector<pair<int, int>> current_bad, next_bad, best_bad;
    int current_score = calc_score(current_bad), best_score = current_score;
    simulated_annealing sa;
    printf("start : %d\n", current_score);
    unsigned short update = 0;
    for (int loop = 0; loop < 2 && current_score > 0; loop++) {
        sa.init();
        while (!sa.end() && current_score > 0) {
            update++;
            if (update == 0) {
                current_score = best_score;
                current_bad = best_bad;
                for (int p = 0; p < plans; p++)
                    for (int i = 0; i <= n * N_MUL; i++) vertex[p][i] = best_vertex[p][i];
                int pos = random::get(1, n * N_MUL - init_len);
                for (int p = 0; p < plans; p++)
                    for (int i = pos; i <= pos + init_len; i++) vertex[p][i] = get_random(result[p][i]);
                current_score = calc_score(current_bad);
            }
            
            if (random::get(100) < 95) {
                int p, pos;
                if (random::get(100) < 30) {
                    auto pair = current_bad[random::get(current_bad.size())];
                    p = pair.first;
                    pos = pair.second;
                } else {
                    p = random::get(plans);
                    pos = random::get(1, n * N_MUL);
                }
                int now = vertex[p][pos], next = get_random(result[p][pos]);
                if (now == next) continue;
                vertex[p][pos] = next;
                int next_score = calc_score(next_bad);
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                    current_bad.swap(next_bad);
                } else {
                    vertex[p][pos] = now;
                }
            } else {
                int p = random::get(plans);
                int pos = random::get(n * N_MUL);
                int from = vertex[p][pos], edge = plan[p][pos], to = vertex[p][pos + 1];
                for (int i = 0; i <= n * N_MUL; i++) tmp_vertex[p][i] = vertex[p][i];
                for (int i = 0; i < n * N_MUL; i++) {
                    if (vertex[p][i] == from && plan[p][i] == edge && vertex[p][i + 1] % 4 == to % 4) vertex[p][i + 1] = to;
                }
                int next_score = calc_score(next_bad);
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                    current_bad.swap(next_bad);
                } else {
                    for (int i = 0; i <= n * N_MUL; i++) vertex[p][i] = tmp_vertex[p][i];
                }
            }
            
            if (current_score < best_score) {
                update = 0;
                best_score = current_score;
                best_bad = current_bad;
                for (int p = 0; p < plans; p++)
                    for (int i = 0; i <= n * N_MUL; i++) best_vertex[p][i] = vertex[p][i];
                fprintf(stderr, "now : %d\n", best_score);
                fflush(stderr);
            }
        }
    }
    printf("end : %d\n", current_score);
    sa.print();
    if (current_score > 0) return 0;
    
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
