use reqwest::header::{HeaderMap, HeaderValue, InvalidHeaderValue};
use serde::{Deserialize, Serialize};
use serde_json::json;

const BASE_URL: &str = "https://wizardry-553250624194.asia-northeast1.run.app/api";
const MOCK_ID: &str = "kenkoooo";
const OFFICIAL_ID: &str = "X6G0RVKUlX20I8XSUsnkIQ";

const PROBLEMS: [(&str, usize); 6] = [
    ("probatio", 3),
    ("primus", 6),
    ("secundus", 12),
    ("tertius", 18),
    ("quartus", 24),
    ("quintus", 30),
];

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub struct ApiClient {
    client: reqwest::Client,
    backend_type: BackendType,
}

#[derive(Clone, Copy)]
pub enum BackendType {
    Mock,
    Official,
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Vertex {
    pub room: usize,
    pub door: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Connection {
    pub from: Vertex,
    pub to: Vertex,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GuessRequestMap {
    pub rooms: Vec<usize>,
    pub starting_room: usize,
    pub connections: Vec<Connection>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GuessResponse {
    pub correct: bool,
}

impl TryFrom<BackendType> for HeaderValue {
    type Error = InvalidHeaderValue;
    fn try_from(backend_type: BackendType) -> std::result::Result<Self, Self::Error> {
        match backend_type {
            BackendType::Mock => "mock".parse(),
            BackendType::Official => "official".parse(),
        }
    }
}

impl ApiClient {
    pub fn new(backend_type: BackendType) -> Result<Self> {
        let mut headers = HeaderMap::new();
        headers.insert("x-backend-type", backend_type.try_into()?);
        let client = reqwest::Client::builder()
            .default_headers(headers)
            .build()?;
        Ok(Self {
            client,
            backend_type,
        })
    }

    pub async fn select(&self, problem_name: &str) -> Result<usize> {
        let problem = PROBLEMS
            .iter()
            .find(|(name, _)| *name == problem_name)
            .ok_or("error: problem not found")?;
        let url = format!("{BASE_URL}/select");
        let id = match self.backend_type {
            BackendType::Mock => MOCK_ID,
            BackendType::Official => OFFICIAL_ID,
        };
        self.client
            .post(url)
            .json(&json!({
                "id": id,
                "problemName": problem.0,
            }))
            .send()
            .await?;
        Ok(problem.1)
    }

    pub async fn explore(&self, plan: &[u8]) -> Result<Vec<usize>> {
        let url = format!("{BASE_URL}/explore");
        let plan = plan
            .iter()
            .map(|&x| x.to_string().chars().collect::<Vec<char>>())
            .flatten()
            .collect::<String>();
        let id = match self.backend_type {
            BackendType::Mock => MOCK_ID,
            BackendType::Official => OFFICIAL_ID,
        };
        let response = self
            .client
            .post(url)
            .json(&json!({
                "id": id,
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

    pub async fn guess(&self, map: &GuessRequestMap) -> Result<bool> {
        let url = format!("{BASE_URL}/guess");
        let id = match self.backend_type {
            BackendType::Mock => MOCK_ID,
            BackendType::Official => OFFICIAL_ID,
        };

        let response = self
            .client
            .post(url)
            .json(&json!({
                "id": id,
                "map": map,
            }))
            .send()
            .await?;
        Ok(response.json::<GuessResponse>().await?.correct)
    }
}

#[derive(Clone)]
pub struct MultiSet<const N: usize> {
    set: [usize; N],
    size: usize,
}

impl<const N: usize> MultiSet<N> {
    pub fn new() -> Self {
        Self {
            set: [0; N],
            size: 0,
        }
    }

    pub fn insert(&mut self, value: usize) {
        self.set[value] += 1;
        self.size += 1;
    }

    pub fn remove(&mut self, value: usize) {
        assert!(self.set[value] > 0);
        self.set[value] -= 1;
        self.size -= 1;
    }

    pub fn len(&self) -> usize {
        self.size
    }

    pub fn to_vec(&self) -> Vec<usize> {
        let mut vec = Vec::new();
        for (i, &count) in self.set.iter().enumerate() {
            for _ in 0..count {
                vec.push(i);
            }
        }
        vec
    }
}
