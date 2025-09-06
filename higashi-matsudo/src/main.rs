use std::{
    collections::BTreeSet,
    fmt::Debug,
    time::{Duration, Instant},
};

use higashi_matsudo::{ApiClient, BackendType, Connection, GuessRequestMap, Vertex};
use rand::Rng;

const SIX: usize = 6;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn generate_random_plan(length: usize, rng: &mut impl Rng) -> Vec<usize> {
    (0..length).map(|_| rng.random_range(0..SIX)).collect()
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let client = ApiClient::new(BackendType::Mock)?;

    // 部屋の数
    let n = client.select("probatio").await?;

    // 移動の履歴
    let a = generate_random_plan(n * 18, &mut rng);

    // 移動した部屋の色
    let b = client.explore(&a).await?;

    let mut color = vec![None; n];
    let mut graph = vec![EdgeSet::new(); n];
    color[0] = Some(b[0]);
    if dfs(0, &mut graph, &mut color, &a, &b[1..], Instant::now()) {
        println!("Found solution");
        fill_graph(&mut graph);
        validate_graph(&graph, &color, &a, &b);

        for v in 0..n {
            if color[v].is_none() {
                color[v] = Some(0);
            }
        }

        let mut set = BTreeSet::new();
        for from in 0..n {
            for forward_door in 0..SIX {
                let (to, backward_door) = graph[from].get(forward_door).expect("no edge");
                let t = graph[to].get(backward_door).expect("no edge");
                assert_eq!(t, (from, forward_door));

                let from = (from, forward_door);
                let to = (to, backward_door);
                let (from, to) = (from.min(to), from.max(to));
                set.insert((from, to));
            }
        }

        let mut rooms = vec![];
        for v in 0..n {
            rooms.push(color[v].expect("no color"));
        }

        let mut connections = vec![];
        for (from, to) in set {
            connections.push(Connection {
                from: Vertex {
                    room: from.0,
                    door: from.1,
                },
                to: Vertex {
                    room: to.0,
                    door: to.1,
                },
            });
        }

        let map = GuessRequestMap {
            rooms,
            starting_room: 0,
            connections,
        };

        let response = client.guess(&map).await?;
        println!("response: {:?}", response);
    } else {
        println!("No solution found");
        println!("n={}", n);
        println!("plan len={} : {:?}", a.len(), a);
        println!("colors len={} : {:?}", b.len(), b);
        return Err("No solution found".into());
    }

    Ok(())
}

fn dfs(
    from: usize,
    graph: &mut [EdgeSet<(usize, usize)>],
    color: &mut Vec<Option<usize>>,
    door_history: &[usize],
    color_history: &[usize],
    start: Instant,
) -> bool {
    assert!(color[from].is_some());
    assert_eq!(door_history.len(), color_history.len());
    let now = Instant::now();
    if now - start > Duration::from_secs(10) {
        return false;
    }
    if door_history.is_empty() {
        return true;
    }

    let n = graph.len();
    let forward_door = door_history[0];
    let next_color = color_history[0];
    for to in 0..n {
        if let Some(a) = graph[from].get(forward_door)
            && a.0 != to
        {
            continue;
        }

        let mut fill_color = false;
        match color[to] {
            Some(current_color) => {
                if current_color != next_color {
                    continue;
                }
            }
            None => {
                color[to] = Some(next_color);
                fill_color = true;
            }
        }
        assert_eq!(color[to], Some(next_color));

        for backward_door in 0..SIX {
            if let Some(a) = graph[from].get(forward_door)
                && a != (to, backward_door)
            {
                continue;
            }
            if let Some(a) = graph[to].get(backward_door)
                && a != (from, forward_door)
            {
                continue;
            }

            if to == from && backward_door == forward_door {
                continue;
            }

            let mut fill_graph = false;
            match graph[from].get(forward_door) {
                None => {
                    // 次数制約は新規にエッジを張る場合のみ確認する
                    if to == from {
                        // 自己ループは同一ノードで2本のドアを消費する
                        if graph[from].len() + 2 > SIX {
                            continue;
                        }
                    } else {
                        if graph[from].len() + 1 > SIX || graph[to].len() + 1 > SIX {
                            continue;
                        }
                    }
                    graph[from].set(forward_door, (to, backward_door));
                    graph[to].set(backward_door, (from, forward_door));
                    fill_graph = true;
                }
                _ => {}
            }

            assert!(graph[to].len() <= 6);
            assert!(graph[from].len() <= 6);

            if dfs(
                to,
                graph,
                color,
                &door_history[1..],
                &color_history[1..],
                start,
            ) {
                return true;
            }

            if fill_graph {
                graph[to].remove(backward_door);
                graph[from].remove(forward_door);
            }
        }

        if fill_color {
            color[to] = None;
        }
    }

    false
}

#[derive(Clone)]
struct EdgeSet<T> {
    size: usize,
    edges: [Option<T>; SIX],
}

impl<T: Copy + Debug> EdgeSet<T> {
    fn new() -> Self {
        Self {
            size: 0,
            edges: [None; SIX],
        }
    }

    fn len(&self) -> usize {
        self.size
    }

    fn set(&mut self, door: usize, target: T) {
        assert!(self.edges[door].is_none());
        self.edges[door] = Some(target);
        self.size += 1;
    }
    fn remove(&mut self, door: usize) {
        assert!(self.edges[door].is_some());
        self.edges[door] = None;
        self.size -= 1;
    }

    fn get(&self, door: usize) -> Option<T> {
        self.edges[door]
    }
}

fn fill_graph(graph: &mut [EdgeSet<(usize, usize)>]) {
    let n = graph.len();
    let mut candidates = vec![];
    for v in 0..n {
        for door in 0..SIX {
            if graph[v].get(door).is_some() {
                continue;
            }

            candidates.push((v, door));
        }
    }

    assert_eq!(candidates.len() % 2, 0);

    while let Some((v1, door1)) = candidates.pop()
        && let Some((v2, door2)) = candidates.pop()
    {
        graph[v1].set(door1, (v2, door2));
        graph[v2].set(door2, (v1, door1));
    }
}

fn validate_graph(
    graph: &[EdgeSet<(usize, usize)>],
    colors: &[Option<usize>],
    plan: &[usize],
    color_history: &[usize],
) {
    let mut from = 0;
    assert_eq!(colors[from], Some(color_history[0]));

    let t = plan.len();
    assert_eq!(t + 1, color_history.len());
    for i in 0..t {
        let door = plan[i];
        let next_color = color_history[i + 1];

        let (to, backward_door) = graph[from].get(door).expect("no edge");

        assert_eq!(colors[to], Some(next_color), "{:?}", color_history);
        let backward = graph[to].get(backward_door).expect("no edge");
        assert_eq!(backward, (from, door));
        from = to;
    }
}
