#include <cstdio>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

const int MAX_N = 90;
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
    constexpr static double TIME_LIMIT = 1;
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

int n, nn;
int plans;
int plan_len;
double temp;
char tmp[MAX_N * N_MUL * 4 + 1];
int plan[MAX_P][MAX_N * N_MUL];
int change[MAX_P][MAX_N * N_MUL];
int result[MAX_P][MAX_N * N_MUL + 1];
int graph[MAX_N][6][3];
int best_graph[MAX_N][6][3];
int final_graph[MAX_N][6];
int label[MAX_N][3];

void input() {
    scanf("%d", &n);
    scanf("%d", &plans);
    scanf("%lf", &temp);
    nn = n / 3;
    plan_len = n * N_MUL;
    for (int p = 0; p < plans; ++p) {
        scanf("%s", tmp);
        for (int i = 0, j = 0; i < plan_len; i++, j++) {
            if (tmp[j] == '[') {
                change[p][i] = tmp[j + 1] - '0';
                j += 3;
            } else {
                change[p][i] = -1;
            }
            plan[p][i] = tmp[j] - '0';
        }
    }
    for (int p = 0; p < plans; ++p) {
        scanf("%s", tmp);
        for (int i = 0, j = 0; i <= plan_len; i++, j++) {
            result[p][i] = tmp[j] - '0';
            if (i < plan_len && change[p][i] != -1) j++;
        }
    }
}

int reverse(int flip) {
    if (flip == 1 || flip == 2) return 3 - flip;
    return flip;
}

int calc_score() {
    int score = 0;
    for (int p = 0; p < plans; p++) {
        int now = 0, flip = 0;
        for (int i = 0; i < nn; i++) {
            for (int j = 0; j < 3; j++) label[i][j] = i % 4;
        }
        for (int i = 0; i < plan_len; i++) {
            if (change[p][i] != -1) label[now][flip] = change[p][i];
            int door = plan[p][i];
            if (graph[now][door][2] == 1) {
                flip = (flip + 1) % 3;
            } else if (graph[now][door][2] == 2) {
                flip = (flip + 2) % 3;
            } else if (graph[now][door][2] == 3) {
                if (flip == 0 || flip == 1) flip = 1 - flip;
            } else if (graph[now][door][2] == 4) {
                if (flip == 0 || flip == 2) flip = 2 - flip;
            } else if (graph[now][door][2] == 5) {
                if (flip == 1 || flip == 2) flip = 3 - flip;
            }
            now = graph[now][door][0];
            if (label[now][flip] != result[p][i + 1]) score++;
        }
    }
    return score;
}

int main() {
    input();
    
    vector<pair<int, int>> candidates;
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            candidates.emplace_back(i, j);
            graph[i][j][0] = -1;
        }
    }
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j][0] != -1) continue;
            int pos = random::get(candidates.size());
            int v = candidates[pos].first, door = candidates[pos].second;
            graph[i][j][0] = v;
            graph[i][j][1] = door;
            graph[v][door][0] = i;
            graph[v][door][1] = j;
            graph[i][j][2] = random::get(6);
            graph[v][door][2] = reverse(graph[i][j][2]);
            candidates.erase(candidates.begin() + pos);
            if (i != v || j != door) candidates.erase(find(candidates.begin(), candidates.end(), make_pair(i, j)));
        }
    }
    
    int current_score = calc_score(), best_score = current_score, last_score = current_score;
    simulated_annealing sa;
    sa.init_temp(temp);
    printf("start : %d\n", current_score);
    unsigned short update = 0;
    for (int loop = 0; loop < 1 && current_score > 0; loop++) {
        sa.init();
        while (!sa.end() && current_score > 0) {
            update++;
            if (update == 0) {
                for (int i = 0; i < nn; i++) {
                    for (int j = 0; j < 6; j++) {
                        for (int k = 0; k < 3; k++) graph[i][j][k] = best_graph[i][j][k];
                    }
                }
                for (int i = 0; i < nn / 2; i++) {
                    int sv1 = random::get(nn), sdoor1 = random::get(6);
                    int tv1 = graph[sv1][sdoor1][0], tdoor1 = graph[sv1][sdoor1][1];
                    bool loop1 = (sv1 == tv1 && sdoor1 == tdoor1);
                    int sv2 = random::get(nn), sdoor2 = random::get(6);
                    int tv2 = graph[sv2][sdoor2][0], tdoor2 = graph[sv2][sdoor2][1];
                    bool loop2 = (sv2 == tv2 && sdoor2 == tdoor2);
                    if ((sv1 == sv2 && sdoor1 == sdoor2) || (sv1 == tv2 && sdoor1 == tdoor2) || (loop1 ^ loop2)) continue;
                    if (loop1 && loop2) {
                        graph[sv1][sdoor1][0] = sv2;
                        graph[sv1][sdoor1][1] = sdoor2;
                        graph[sv2][sdoor2][0] = sv1;
                        graph[sv2][sdoor2][1] = sdoor1;
                        graph[sv1][sdoor1][2] = random::get(6);
                        graph[sv2][sdoor2][2] = reverse(graph[sv1][sdoor1][2]);
                    } else {
                        graph[sv1][sdoor1][0] = tv2;
                        graph[sv1][sdoor1][1] = tdoor2;
                        graph[tv1][tdoor1][0] = sv2;
                        graph[tv1][tdoor1][1] = sdoor2;
                        graph[sv2][sdoor2][0] = tv1;
                        graph[sv2][sdoor2][1] = tdoor1;
                        graph[tv2][tdoor2][0] = sv1;
                        graph[tv2][tdoor2][1] = sdoor1;
                        graph[sv1][sdoor1][2] = random::get(6);
                        graph[sv2][sdoor2][2] = random::get(6);
                        graph[tv1][tdoor1][2] = reverse(graph[sv2][sdoor2][2]);
                        graph[tv2][tdoor2][2] = reverse(graph[sv1][sdoor1][2]);
                    }
                }
                current_score = calc_score();
            }
            
            int select = random::get(100);
            if (select < 50) {
                int sv1 = random::get(nn), sdoor1 = random::get(6);
                int tv1 = graph[sv1][sdoor1][0], tdoor1 = graph[sv1][sdoor1][1];
                int flip11 = graph[sv1][sdoor1][2], flip12 = graph[tv1][tdoor1][2];
                bool loop1 = (sv1 == tv1 && sdoor1 == tdoor1);
                int sv2 = random::get(nn), sdoor2 = random::get(6);
                int tv2 = graph[sv2][sdoor2][0], tdoor2 = graph[sv2][sdoor2][1];
                int flip21 = graph[sv2][sdoor2][2], flip22 = graph[tv2][tdoor2][2];
                bool loop2 = (sv2 == tv2 && sdoor2 == tdoor2);
                if ((sv1 == sv2 && sdoor1 == sdoor2) || (sv1 == tv2 && sdoor1 == tdoor2) || (loop1 ^ loop2)) continue;
                if (loop1 && loop2) {
                    graph[sv1][sdoor1][0] = sv2;
                    graph[sv1][sdoor1][1] = sdoor2;
                    graph[sv2][sdoor2][0] = sv1;
                    graph[sv2][sdoor2][1] = sdoor1;
                    graph[sv1][sdoor1][2] = flip11;
                    graph[sv2][sdoor2][2] = reverse(flip11);
                } else {
                    graph[sv1][sdoor1][0] = tv2;
                    graph[sv1][sdoor1][1] = tdoor2;
                    graph[tv1][tdoor1][0] = sv2;
                    graph[tv1][tdoor1][1] = sdoor2;
                    graph[sv2][sdoor2][0] = tv1;
                    graph[sv2][sdoor2][1] = tdoor1;
                    graph[tv2][tdoor2][0] = sv1;
                    graph[tv2][tdoor2][1] = sdoor1;
                    graph[sv1][sdoor1][2] = flip11;
                    graph[tv1][tdoor1][2] = flip22;
                    graph[sv2][sdoor2][2] = flip21;
                    graph[tv2][tdoor2][2] = flip12;
                }
                int next_score = calc_score();
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                } else {
                    graph[sv1][sdoor1][0] = tv1;
                    graph[sv1][sdoor1][1] = tdoor1;
                    graph[tv1][tdoor1][0] = sv1;
                    graph[tv1][tdoor1][1] = sdoor1;
                    graph[sv2][sdoor2][0] = tv2;
                    graph[sv2][sdoor2][1] = tdoor2;
                    graph[tv2][tdoor2][0] = sv2;
                    graph[tv2][tdoor2][1] = sdoor2;
                    graph[sv1][sdoor1][2] = flip11;
                    graph[tv1][tdoor1][2] = flip12;
                    graph[sv2][sdoor2][2] = flip21;
                    graph[tv2][tdoor2][2] = flip22;
                }
            } else if (select < 55) {
                int sv = random::get(nn), sdoor = random::get(6);
                int tv = graph[sv][sdoor][0], tdoor = graph[sv][sdoor][1];
                if (sv == tv && sdoor == tdoor) continue;
                graph[sv][sdoor][0] = sv;
                graph[sv][sdoor][1] = sdoor;
                graph[tv][tdoor][0] = tv;
                graph[tv][tdoor][1] = tdoor;
                int next_score = calc_score();
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                } else {
                    graph[sv][sdoor][0] = tv;
                    graph[sv][sdoor][1] = tdoor;
                    graph[tv][tdoor][0] = sv;
                    graph[tv][tdoor][1] = sdoor;
                }
            } else {
                int sv = random::get(nn), sdoor = random::get(6);
                int tv = graph[sv][sdoor][0], tdoor = graph[sv][sdoor][1];
                int flip1 = graph[sv][sdoor][2], flip2 = graph[tv][tdoor][2];
                graph[sv][sdoor][2] = random::get(6);
                graph[tv][tdoor][2] = reverse(graph[sv][sdoor][2]);
                int next_score = calc_score();
                if (sa.accept(current_score, next_score)) {
                    current_score = next_score;
                } else {
                    graph[sv][sdoor][2] = flip1;
                    graph[tv][tdoor][2] = flip2;
                }
            }
            
            if (current_score < best_score) {
                update = 0;
                best_score = current_score;
                for (int i = 0; i < nn; i++) {
                    for (int j = 0; j < 6; j++) {
                        for (int k = 0; k < 3; k++) best_graph[i][j][k] = graph[i][j][k];
                    }
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
    
    for (int i = 0; i < nn; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j][2] == 0) {
                final_graph[i][j] = graph[i][j][0];
                final_graph[i + nn][j] = graph[i][j][0] + nn;
                final_graph[i + nn * 2][j] = graph[i][j][0] + nn * 2;
            } else if (graph[i][j][2] == 1) {
                final_graph[i][j] = graph[i][j][0] + nn;
                final_graph[i + nn][j] = graph[i][j][0] + nn * 2;
                final_graph[i + nn * 2][j] = graph[i][j][0];
            } else if (graph[i][j][2] == 2) {
                final_graph[i][j] = graph[i][j][0] + nn * 2;
                final_graph[i + nn][j] = graph[i][j][0];
                final_graph[i + nn * 2][j] = graph[i][j][0] + nn;
            } else if (graph[i][j][2] == 3) {
                final_graph[i][j] = graph[i][j][0] + nn;
                final_graph[i + nn][j] = graph[i][j][0];
                final_graph[i + nn * 2][j] = graph[i][j][0] + nn * 2;
            } else if (graph[i][j][2] == 4) {
                final_graph[i][j] = graph[i][j][0] + nn * 2;
                final_graph[i + nn][j] = graph[i][j][0] + nn;
                final_graph[i + nn * 2][j] = graph[i][j][0];
            } else {
                final_graph[i][j] = graph[i][j][0];
                final_graph[i + nn][j] = graph[i][j][0] + nn * 2;
                final_graph[i + nn * 2][j] = graph[i][j][0] + nn;
            }
        }
    }
    
    puts("0");
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) printf("%d %d ", final_graph[i][j], graph[i % nn][j][1]);
    }
    puts("");
    puts("solved");
    
    return 0;
}
