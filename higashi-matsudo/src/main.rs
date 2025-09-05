use higashi_matsudo::{ApiClient, BackendType, Connection, GuessRequestMap, Vertex};
use rand::{Rng, seq::SliceRandom};
use rayon::iter::{IntoParallelIterator, ParallelIterator};

const SIX: usize = 6;
const LABEL: usize = 4;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn generate_random_plan(length: usize, rng: &mut impl Rng) -> Vec<usize> {
    (0..length).map(|_| rng.random_range(0..SIX)).collect()
}

#[derive(Clone)]
struct Graph {
    labels: Vec<usize>,
    g: Vec<[(usize, usize); 6]>,
}

impl Graph {
    fn new(v: usize, rng: &mut impl Rng) -> Self {
        let mut g = vec![[(0, 0); 6]; v];

        let mut candidates = vec![];
        for i in 0..v {
            for j in 0..SIX {
                candidates.push((i, j));
            }
        }

        candidates.shuffle(rng);

        while candidates.len() >= 2 {
            let n = candidates.len();
            let two = candidates.split_off(n - 2);

            assert_eq!(candidates.len(), n - 2);
            assert_eq!(two.len(), 2);

            let (v0, door0) = two[0];
            let (v1, door1) = two[1];
            g[v0][door0] = (v1, door1);
            g[v1][door1] = (v0, door0);
        }

        Self {
            labels: (0..v).map(|_| rng.random_range(0..LABEL)).collect(),
            g,
        }
    }

    fn run(&self, plan: &[usize]) -> Vec<usize> {
        let mut result = vec![self.labels[0]];
        let mut cur = 0;
        for &door in plan {
            let (next, _) = self.g[cur][door];
            result.push(self.labels[next]);
            cur = next;
        }
        result
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let client = ApiClient::new(BackendType::Mock)?;

    let n = client.select("probatio").await?;
    let plan = generate_random_plan(n * 18, &mut rng);
    let result = client.explore(&plan).await?;
    loop {
        let (best, score) = (0..20)
            .into_par_iter()
            .map(|_| {
                let mut rng = rand::rng();
                let (graph, score) =
                    simulated_annealing(&Graph::new(n, &mut rng), &mut rng, &plan, &result);
                (graph, score)
            })
            .min_by_key(|(_, score)| *score)
            .unwrap();
        println!("Score: {}", score);
        if score == 0 {
            let mut connections = vec![];
            let rooms = best.labels;
            for (from, edges) in best.g.into_iter().enumerate() {
                for (from_door, (next, next_door)) in edges.into_iter().enumerate() {
                    let from = (from, from_door);
                    let to = (next, next_door);
                    if from > to {
                        continue;
                    }
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
            }

            let correct = client
                .guess(&GuessRequestMap {
                    rooms,
                    starting_room: 0,
                    connections,
                })
                .await?;
            if correct {
                println!("Correct!");
                break;
            }

            break;
        }
    }
    Ok(())
}

fn switch_label(graph: &mut Graph, rng: &mut impl Rng) {
    let v = rng.random_range(0..graph.labels.len());
    let label = rng.random_range(0..LABEL);
    graph.labels[v] = label;
}

fn switch_edge(graph: &mut Graph, rng: &mut impl Rng) {
    let n = graph.labels.len();
    loop {
        let v0 = rng.random_range(0..n);
        let v1 = rng.random_range(0..n);
        let door0 = rng.random_range(0..SIX);
        let door1 = rng.random_range(0..SIX);
        let from0 = (v0, door0);
        let from1 = (v1, door1);
        if from0 == from1 {
            continue;
        }
        let to0 = graph.g[v0][door0];
        if to0 == from1 {
            continue;
        }
        let to1 = graph.g[v1][door1];

        graph.g[from0.0][from0.1] = to1;
        graph.g[from1.0][from1.1] = to0;
        graph.g[to0.0][to0.1] = from1;
        graph.g[to1.0][to1.1] = from0;
        break;
    }
}

fn score(graph: &Graph, plan: &[usize], result: &[usize]) -> usize {
    let current = graph.run(plan);
    assert_eq!(current.len(), result.len());
    let n = current.len();

    let mut dp = vec![vec![0; n + 1]; n + 1];
    for i in 0..=n {
        for j in 0..=n {
            dp[i][j] = if i == 0 && j == 0 {
                0
            } else if i == 0 {
                j
            } else if j == 0 {
                i
            } else {
                dp[i - 1][j - 1]
                    + if current[i - 1] == result[j - 1] {
                        0
                    } else {
                        1
                    }
            };
        }
    }
    dp[current.len()][result.len()]
}

fn simulated_annealing(
    graph: &Graph,
    rng: &mut impl Rng,
    plan: &[usize],
    result: &[usize],
) -> (Graph, usize) {
    let mut best_score = score(graph, plan, result);
    let mut best_graph = graph.clone();
    let mut current_score = best_score;
    let mut current_graph = graph.clone();
    // 反復ベースの指数冷却
    const MAX_STEPS: usize = 400_000;
    const T0: f64 = 5.0;
    const T_END: f64 = 0.001;
    let mut steps = 0usize;
    for step in 0..MAX_STEPS {
        let progress = step as f64 / MAX_STEPS as f64;
        let temperature = T0 * (T_END / T0).powf(progress);
        let mut new_graph = current_graph.clone();

        if rng.random_range(0.0..1.0) < 0.5 + 0.3 * progress {
            switch_label(&mut new_graph, rng);
        } else {
            switch_edge(&mut new_graph, rng);
        }

        let new_score = score(&new_graph, plan, result);
        if new_score <= current_score {
            current_score = new_score;
            current_graph = new_graph;
            if current_score < best_score {
                best_score = current_score;
                best_graph = current_graph.clone();
            }
        } else {
            let delta = (new_score - current_score) as f64;
            let probability = (-delta / temperature).exp();
            if rng.random_range(0.0..1.0) < probability {
                current_score = new_score;
                current_graph = new_graph;
            }
        }
        steps += 1;
        if steps % 10000 == 0 {
            println!(
                "Steps: {}  Temp: {:.4}  Current: {}  Best: {}",
                steps, temperature, current_score, best_score
            );
        }

        if best_score == 0 {
            break;
        }
    }

    (best_graph, best_score)
}
