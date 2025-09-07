#include "globals.h"

// 定数の定義
const int MAX_N = 30;
const int N_MUL = 6;
const int MAX_P = 10;

// 共通グローバル変数の定義
int n = 30;
int plans = 1;
int plan[MAX_P][MAX_N * N_MUL];
int result[MAX_P][MAX_N * N_MUL + 1];
int vertex[MAX_P][MAX_N * N_MUL + 1];
int tmp_vertex[MAX_P][MAX_N * N_MUL + 1];
int best_vertex[MAX_P][MAX_N * N_MUL + 1];
int graph[MAX_N][6];
