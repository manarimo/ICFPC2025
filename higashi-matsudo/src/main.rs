use higashi_matsudo::{ApiClient, BackendType};
use rand::Rng;

const SIX: usize = 6;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn generate_random_plan(length: usize, rng: &mut impl Rng) -> Vec<usize> {
    (0..length).map(|_| rng.random_range(0..SIX)).collect()
}

// 再構成: N, A(長さL), B(長さL+1) から訪れた部屋番号列(長さL+1)を1つ構成する
// 重要: A[i] は「入る側（到着先の部屋）でのドア番号」を表す。
// つまり、R_i から R_{i+1} へ移動したとき、到着先 R_{i+1} のドア A[i] は、出発元 R_i と接続している。
fn reconstruct_path(n: usize, a: &[usize], b: &[usize]) -> Vec<usize> {
    assert_eq!(b.len(), a.len() + 1);

    // colors[v] は部屋 v の色（生成済みであれば Some）。
    let mut colors: Vec<Option<usize>> = vec![None; n];
    colors[0] = Some(b[0]);

    // in_edges[v][p] = Some(from) は、部屋 v のドア p（入る側）に接続している出発元の部屋 ID。
    let mut in_edges: Vec<[Option<usize>; SIX]> = vec![[None; SIX]; n];

    // 現時点で生成済みの部屋数。
    let mut room_count = 1usize;

    let l = a.len();
    let mut path: Vec<usize> = vec![0; l + 1];

    // バックトラッキング用の操作ログ
    enum Action {
        SetInEdge { room: usize, port: usize },
        NewRoom { room: usize },
    }
    let mut actions: Vec<Action> = Vec::new();

    // 各ステップでの候補と選択位置を管理
    #[derive(Clone, Copy)]
    enum Cand {
        Existing(usize),
        New,
    }
    struct Frame {
        i: usize,
        cands: Vec<Cand>,
        next_idx: usize,
        actions_len_before: usize,
    }
    let mut choice_stack: Vec<Frame> = Vec::new();

    let mut i = 0usize;
    while i < l {
        let from = path[i];
        let port_enter = a[i];
        let need_color = b[i + 1];

        // 候補生成（優先度順）
        let mut cands: Vec<Cand> = Vec::new();
        // 1) 既存で in_edges[v][port]==Some(from)
        for v in 0..room_count {
            if colors[v] == Some(need_color) {
                if let Some(prev_from) = in_edges[v][port_enter] {
                    if prev_from == from {
                        cands.push(Cand::Existing(v));
                    }
                }
            }
        }
        // 2) 新規
        if room_count < n {
            cands.push(Cand::New);
        }
        // 3) 既存で in_edges[v][port]==None
        for v in 0..room_count {
            if colors[v] == Some(need_color) && in_edges[v][port_enter].is_none() {
                cands.push(Cand::Existing(v));
            }
        }

        // 既に選択済みで次候補を試す場合に備え、スタックを参照
        let mut start_idx = 0usize;
        if let Some(frame) = choice_stack.last() {
            if frame.i == i {
                start_idx = frame.next_idx;
            } else {
                // 異なる i に進んだ場合は、新しい候補セットを使う
            }
        }

        // 候補がなければバックトラック
        if cands.is_empty() || start_idx >= cands.len() {
            // バックトラック
            let Some(mut frame) = choice_stack.pop() else {
                // 解なし（理論上は起こらない想定）
                break;
            };
            // 直前の選択で行った操作を巻き戻す（その選択以降のアクションのみ）
            while actions.len() > frame.actions_len_before {
                let action = actions.pop().unwrap();
                match action {
                    Action::SetInEdge { room, port } => {
                        in_edges[room][port] = None;
                    }
                    Action::NewRoom { room } => {
                        // その部屋の初期化を戻す
                        room_count -= 1;
                        debug_assert_eq!(room, room_count);
                        colors[room] = None;
                        in_edges[room] = [None; SIX];
                    }
                }
            }
            // 前回の候補の次を試す
            frame.next_idx += 1;
            if frame.next_idx < frame.cands.len() {
                let prev_i = frame.i;
                choice_stack.push(frame);
                i = prev_i; // その位置から再試行
                continue;
            } else {
                // さらにバックトラック
                i = frame.i; // 位置だけ戻す（ループ先頭で更にpopされる）
                continue;
            }
        }

        // 今回の候補セットを記録（start_idx から試す）
        let actions_len_before = actions.len();
        choice_stack.push(Frame { i, cands: cands.clone(), next_idx: start_idx, actions_len_before });

        let cand = cands[start_idx];
        match cand {
            Cand::Existing(to) => {
                if in_edges[to][port_enter].is_none() {
                    in_edges[to][port_enter] = Some(from);
                    actions.push(Action::SetInEdge { room: to, port: port_enter });
                }
                // 色は既に一致している前提
                path[i + 1] = to;
                i += 1;
            }
            Cand::New => {
                let to = room_count;
                // 新規作成
                colors[to] = Some(need_color);
                in_edges[to] = [None; SIX];
                room_count += 1;
                actions.push(Action::NewRoom { room: to });
                // in_edges を接続
                in_edges[to][port_enter] = Some(from);
                actions.push(Action::SetInEdge { room: to, port: port_enter });

                path[i + 1] = to;
                i += 1;
            }
        }
    }

    path
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let client = ApiClient::new(BackendType::Mock)?;

    // 部屋の数
    let n = client.select("secundus").await?;

    // 移動の履歴
    let a = generate_random_plan(n * 18, &mut rng);

    // 移動した部屋の色
    let b = client.explore(&a).await?;

    // 訪れた部屋番号列を再構成（複数解のうち1つ）
    let rooms_path = reconstruct_path(n, &a, &b);

    // 出力の検証
    assert_eq!(rooms_path.len(), a.len() + 1);

    // 入る側の検証: 到着先 to のドア a[i] は、出発元 from と一意に接続されているべき
    let mut graph_in = vec![vec![None; SIX]; n];
    for (i, &door_enter) in a.iter().enumerate() {
        let from = rooms_path[i];
        let to = rooms_path[i + 1];
        match graph_in[to][door_enter] {
            None => {
                graph_in[to][door_enter] = Some(from);
            }
            Some(prev) => {
                assert_eq!(
                    prev, from,
                    "a={:?}, b={:?}, the entering door {door_enter} of room {to} is already connected from {prev}, but trying to connect from {from}",
                    a, b
                );
            }
        }
    }

    let mut colors = vec![None; n];
    for (i, &color) in b.iter().enumerate() {
        let room = rooms_path[i];
        match colors[room] {
            None => {
                colors[room] = Some(color);
            }
            Some(prev) => {
                assert_eq!(
                    prev, color,
                    "a={:?}, b={:?}, the room color of {room} is already defined as {prev}, but trying to define as {color}",
                    a, b
                );
            }
        }
    }

    println!("ooooooooo");

    Ok(())
}
