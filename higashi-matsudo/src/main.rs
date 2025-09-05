use rand::{Rng, seq::SliceRandom};
use reqwest::header::HeaderMap;
use serde::Deserialize;
use serde_json::json;

const SIX: usize = 6;
const LABEL: usize = 4;

const BASE_URL: &str = "https://wizardry-553250624194.asia-northeast1.run.app/api";
const ID: &str = "kenkoooo";

const PROBLEMS: [(&str, usize); 6] = [
    ("probatio", 3),
    ("primus", 6),
    ("secundus", 12),
    ("tertius", 18),
    ("quartus", 24),
    ("quintus", 30),
];

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

struct ApiClient {
    client: reqwest::Client,
}

impl ApiClient {
    fn new() -> Result<Self> {
        let mut headers = HeaderMap::new();
        headers.insert("x-backend-type", "mock".parse()?);
        let client = reqwest::Client::builder()
            .default_headers(headers)
            .build()?;
        Ok(Self { client })
    }

    async fn select(&self, problem_name: &str) -> Result<usize> {
        let problem = PROBLEMS
            .iter()
            .find(|(name, _)| *name == problem_name)
            .ok_or("error: problem not found")?;
        let url = format!("{BASE_URL}/select");
        self.client
            .post(url)
            .json(&json!({
                "id": ID,
                "problemName": problem.0,
            }))
            .send()
            .await?;
        Ok(problem.1)
    }

    async fn explore(&self, plan: &[usize]) -> Result<Vec<usize>> {
        let url = format!("{BASE_URL}/explore");
        let plan = plan
            .iter()
            .map(|&x| x.to_string().chars().collect::<Vec<char>>())
            .flatten()
            .collect::<String>();
        let response = self
            .client
            .post(url)
            .json(&json!({
                "id": ID,
                "plans": [plan],
            }))
            .send()
            .await?;

        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase")]
        struct Response {
            results: Vec<Vec<usize>>,
        }

        let response = response.json::<Response>().await?;
        Ok(response.results.into_iter().flatten().collect())
    }
}

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
    let client = ApiClient::new()?;

    let n = client.select("probatio").await?;
    let plan = generate_random_plan(n * 18, &mut rng);
    let result = client.explore(&plan).await?;
    let (graph, _) = simulated_annealing(&Graph::new(n, &mut rng), &mut rng, &plan, &result);
    println!("Score: {}", score(&graph, &plan, &result));

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
    let max_steps: usize = 50000;
    let t0: f64 = 5.0;
    let t_end: f64 = 0.01;
    let mut steps = 0usize;
    for step in 0..max_steps {
        let progress = step as f64 / max_steps as f64;
        let temperature = t0 * (t_end / t0).powf(progress);
        let mut new_graph = current_graph.clone();

        if rng.random_range(0.0..1.0) < 0.5 {
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
        if steps % 1000 == 0 {
            println!("Steps: {}  Temp: {:.4}  Current: {}  Best: {}", steps, temperature, current_score, best_score);
        }

        if best_score == 0 {
            break;
        }
    }

    (best_graph, best_score)
}
