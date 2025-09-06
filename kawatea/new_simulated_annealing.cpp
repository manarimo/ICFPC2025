#include <cstdio>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

const int MAX_N = 30;

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
    constexpr static double TIME_LIMIT = 30;
    constexpr static double START_TEMP = 1;
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

int n = 24;
int plan[MAX_N * 18];
int result[MAX_N * 18 + 1];
int vertex[MAX_N * 18 + 1];
int best_vertex[MAX_N * 18 + 1];
int graph[MAX_N][6];
int cnt[MAX_N][6];
vector<int> candidate[4];

int get_random(int bit) {
    return candidate[bit][random::get(candidate[bit].size())];
}

int calc_score(vector<int>& bad) {
    bad.clear();
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            graph[i][j] = -1;
            cnt[i][j] = 0;
        }
    }
    
    int score = 0;
    for (int i = 0; i < n * 18; i++) {
        if (cnt[vertex[i]][plan[i]] == 0) {
            graph[vertex[i]][plan[i]] = vertex[i + 1];
            cnt[vertex[i]][plan[i]] = 1;
        } else if (graph[vertex[i]][plan[i]] == vertex[i + 1]) {
            cnt[vertex[i]][plan[i]]++;
        } else {
            cnt[vertex[i]][plan[i]]--;
        }
    }
    for (int i = 0; i < n * 18; i++) {
        if (graph[vertex[i]][plan[i]] != vertex[i + 1]) {
            if (i > 0) bad.push_back(i);
            bad.push_back(i + 1);
            score++;
        }
    }
    return score;
}

int main() {
    for (int i = 0; i < n * 18; i++) {
        plan[i] = random::get(6);
        printf("%d", plan[i]);
    }
    puts("");
    for (int i = 0; i <= n * 18; i++) scanf("%1d", &result[i]);
    
    for (int i = 0; i < n; i++) candidate[i % 4].push_back(i);
    for (int i = 1; i <= n * 18; i++) vertex[i] = best_vertex[i] = get_random(result[i]);
    vector<int> current_bad, next_bad, best_bad;
    int current_score = calc_score(current_bad), best_score = current_score;
    simulated_annealing sa;
    printf("start : %d\n", current_score);
    unsigned short update = 0;
    for (int loop = 0; loop < 20 && current_score > 0; loop++) {
        sa.init();
        while (!sa.end() && current_score > 0) {
            update++;
            if (update == 0) {
                current_score = best_score;
                current_bad = best_bad;
                for (int i = 0; i <= n * 18; i++) vertex[i] = best_vertex[i];
            }
            
            int pos;
            if (random::get(100) < 30) {
                pos = current_bad[random::get(current_bad.size())];
            } else {
                pos = random::get(1, n * 18);
            }
            int now = vertex[pos];
            int next = get_random(result[pos]);
            if (now == next) continue;
            vertex[pos] = next;
            int next_score = calc_score(next_bad);
            if (sa.accept(current_score, next_score)) {
                current_score = next_score;
                current_bad.swap(next_bad);
                if (current_score < best_score) {
                    update = 0;
                    best_score = current_score;
                    best_bad = current_bad;
                    for (int i = 0; i <= n * 18; i++) best_vertex[i] = vertex[i];
                    printf("now : %d\n", best_score);
                    fflush(stdout);
                }
            } else {
                vertex[pos] = now;
            }
        }
    }
    printf("end : %d\n", current_score);
    sa.print();
    if (current_score > 0) return 0;
    
    bool all = true;
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
                if (parent[i].size() > 1) all = false;
                graph[i][j] = parent[i].back();
                parent[i].pop_back();
            } else {
                all = false;
                graph[i][j] = i;
            }
        }
    }
    
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) printf("%d ", graph[i][j]);
    }
    puts("");
    if (all) puts("solved");
    
    return 0;
}
