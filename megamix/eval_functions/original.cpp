#include "score.h"
#include <algorithm>

using namespace std;

static int cnt[30][6];    // MAX_N * 6
static int in_cnt[30][30]; // MAX_N * MAX_N
static int out_cnt[30][30]; // MAX_N * MAX_N
static int sum_cnt[30];   // MAX_N

int calc_score(vector<pair<int, int>>& bad) {
    bad.clear();
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            graph[i][j] = -1;
            cnt[i][j] = 0;
        }
        for (int j = 0; j < n; j++) in_cnt[i][j] = out_cnt[i][j] = 0;
    }
    
    int score = 0;
    for (int p = 0; p < plans; p++) {        
        for (int i = 0; i < n * N_MUL; i++) {
            if (cnt[vertex[p][i]][plan[p][i]] == 0) {
                graph[vertex[p][i]][plan[p][i]] = vertex[p][i + 1];
                cnt[vertex[p][i]][plan[p][i]] = 1;
            } else if (graph[vertex[p][i]][plan[p][i]] == vertex[p][i + 1]) {
                cnt[vertex[p][i]][plan[p][i]]++;
            } else {
                cnt[vertex[p][i]][plan[p][i]]--;
            }
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
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < 6; j++) {
            if (graph[i][j] != -1) {
                in_cnt[graph[i][j]][i]++;
                out_cnt[i][graph[i][j]]++;
            }
        }
    }
    for (int i = 0; i < n; i++) {
        sum_cnt[i] = 0;
        for (int j = 0; j < n; j++) sum_cnt[i] += max(in_cnt[i][j], out_cnt[i][j]);
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
    return score;
}
