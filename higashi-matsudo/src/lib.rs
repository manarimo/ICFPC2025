pub mod union_find;

use reqwest::header::{HeaderMap, HeaderValue, InvalidHeaderValue};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

const BASE_URL: &str = "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com";
const MOCK_ID: &str = "kenkoooo";
const OFFICIAL_ID: &str = "amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ";

#[derive(Clone, Copy)]
pub enum Problem {
    Probatio,
    Primus,
    Secundus,
    Tertius,
    Quartus,
    Quintus,
    Aleph,
    Beth,
    Gimel,
    Daleth,
    He,
    Vau,
    Zain,
    Hhet,
    Teth,
    Iod,
}

impl Problem {
    pub fn to_str(&self) -> &str {
        match self {
            Problem::Probatio => "probatio",
            Problem::Primus => "primus",
            Problem::Secundus => "secundus",
            Problem::Tertius => "tertius",
            Problem::Quartus => "quartus",
            Problem::Quintus => "quintus",
            Problem::Aleph => "aleph",
            Problem::Beth => "beth",
            Problem::Gimel => "gimel",
            Problem::Daleth => "daleth",
            Problem::He => "he",
            Problem::Vau => "vau",
            Problem::Zain => "zain",
            Problem::Hhet => "hhet",
            Problem::Teth => "teth",
            Problem::Iod => "iod",
        }
    }

    pub fn problem_size(&self) -> usize {
        match self {
            Problem::Probatio => 3,
            Problem::Primus => 6,
            Problem::Secundus => 12,
            Problem::Tertius => 18,
            Problem::Quartus => 24,
            Problem::Quintus => 30,
            Problem::Aleph => 12,
            Problem::Beth => 24,
            Problem::Gimel => 36,
            Problem::Daleth => 48,
            Problem::He => 60,
            Problem::Vau => 18,
            Problem::Zain => 36,
            Problem::Hhet => 54,
            Problem::Teth => 72,
            Problem::Iod => 90,
        }
    }
}

pub(crate) type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub struct ApiClient {
    client: reqwest::Client,
    backend_type: BackendType,
}

#[derive(Clone, Copy)]
pub enum BackendType {
    Mock,
    Official,
}

impl BackendType {
    pub fn directory(&self) -> &str {
        match self {
            BackendType::Mock => "mock",
            BackendType::Official => "graph-dump",
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Vertex {
    pub room: usize,
    pub door: usize,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Connection {
    pub from: Vertex,
    pub to: Vertex,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct GuessRequestMap {
    pub rooms: Vec<u8>,
    pub starting_room: usize,
    pub connections: Vec<Connection>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GuessResponse {
    pub correct: bool,
}

#[derive(Debug, Clone, Copy)]
pub enum Event {
    VisitRoom { label: u8 },
    Overwrite { label: u8 },
    OpenDoor { door: usize },
}

#[derive(Debug, Clone, Copy)]
pub enum ExploreQuery {
    Open { door: usize },
    Charcoal { label: u8 },
}

impl ExploreQuery {
    pub fn open(door: usize) -> Self {
        Self::Open { door }
    }

    pub fn charcoal(label: u8) -> Self {
        Self::Charcoal { label }
    }
}

impl ToString for ExploreQuery {
    fn to_string(&self) -> String {
        match self {
            ExploreQuery::Open { door } => door.to_string(),
            ExploreQuery::Charcoal { label } => format!("[{}]", label),
        }
    }
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

    pub async fn select(&self, problem: Problem) -> Result<()> {
        let url = format!("{BASE_URL}/select");
        let id = match self.backend_type {
            BackendType::Mock => MOCK_ID,
            BackendType::Official => OFFICIAL_ID,
        };
        self.client
            .post(url)
            .json(&json!({
                "id": id,
                "problemName": problem.to_str(),
            }))
            .send()
            .await?;
        Ok(())
    }

    pub async fn explore(&self, plans: &[Vec<ExploreQuery>]) -> Result<Vec<Vec<Event>>> {
        let url = format!("{BASE_URL}/explore");
        let mut queries = vec![];
        for plan in plans {
            let query = plan
                .iter()
                .map(|&x| x.to_string())
                .collect::<Vec<String>>()
                .join("");
            queries.push(query);
        }
        let id = match self.backend_type {
            BackendType::Mock => MOCK_ID,
            BackendType::Official => OFFICIAL_ID,
        };
        let request = json!({
            "id": id,
            "plans": queries,
        });
        let response = self.client.post(url).json(&request).send().await?;

        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase")]
        struct Response {
            results: Vec<Vec<u8>>,
        }

        let response = response.json::<Value>().await?;
        let response = serde_json::from_value::<Response>(response)?;

        let mut batch = vec![];
        for (results, plan) in response.results.iter().zip(plans) {
            let mut events = vec![];
            events.push(Event::VisitRoom { label: results[0] });

            for (&result, &plan) in results.iter().skip(1).zip(plan.iter()) {
                match plan {
                    ExploreQuery::Open { door } => {
                        events.push(Event::OpenDoor { door });
                        events.push(Event::VisitRoom { label: result });
                    }
                    ExploreQuery::Charcoal { label } => {
                        events.push(Event::Overwrite { label });
                    }
                }
            }
            batch.push(events);
        }

        Ok(batch)
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
