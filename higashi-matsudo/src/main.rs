use rand::Rng;
use reqwest::header::HeaderMap;
use serde::Deserialize;
use serde_json::json;

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
        let response = self
            .client
            .post(url)
            .json(&json!({
                "id": ID,
                "problemName": problem.0,
            }))
            .send()
            .await?;
        Ok(problem.1)
    }

    async fn explore(&self, plan: &str) -> Result<Vec<i32>> {
        let url = format!("{BASE_URL}/explore");
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
            results: Vec<Vec<i32>>,
        }

        let response = response.json::<Response>().await?;
        Ok(response.results.into_iter().flatten().collect())
    }
}

fn generate_random_plan(length: usize) -> String {
    let mut rng = rand::rng();
    let digits: &[u8] = b"012345";
    (0..length)
        .map(|_| digits[rng.random_range(0..digits.len())] as char)
        .collect()
}

#[tokio::main]
async fn main() -> Result<()> {
    let client = ApiClient::new()?;
    let n = client.select("probatio").await?;
    let plan = generate_random_plan(n * 18);
    let results = client.explore(&plan).await?;
    println!("{}", plan);
    println!("{:?}", results);
    Ok(())
}
