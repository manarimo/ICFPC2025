#ifndef GLOBALS_H
#define GLOBALS_H

// 定数の宣言
extern const int MAX_N;
extern const int N_MUL;
extern const int MAX_P;

// 共通グローバル変数の宣言
extern int n;
extern int plans;
extern int plan[10][180];  // MAX_P * MAX_N * N_MUL
extern int result[10][181]; // MAX_P * (MAX_N * N_MUL + 1)
extern int vertex[10][181]; // MAX_P * (MAX_N * N_MUL + 1)
extern int tmp_vertex[10][181]; // MAX_P * (MAX_N * N_MUL + 1)
extern int best_vertex[10][181]; // MAX_P * (MAX_N * N_MUL + 1)
extern int graph[30][6]; // MAX_N * 6

#endif // GLOBALS_H
