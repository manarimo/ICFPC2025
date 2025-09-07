use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    fs::{File, read_to_string},
    io::Write as _,
    path::Path,
    time::{SystemTime, UNIX_EPOCH},
};

use higashi_matsudo::{
    ApiClient, BackendType, Connection, Event, ExploreQuery, GuessRequestMap, Problem, Vertex,
    union_find::UnionFind,
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let backend_type = BackendType::Official;
    let client = ApiClient::new(backend_type)?;
    let problem = Problem::Beth;

    // list all files in the directory

    let path = Path::new("../graph-dump").join(problem.to_str());
    let files = std::fs::read_dir(path)?;
    for file in files {
        let file = file?;
        let file = file.path();
        let json = serde_json::from_str::<GuessRequestMap>(&read_to_string(file)?)?;

        client.select(problem).await?;
        let correct = client.guess(&json).await?;
        if correct {
            eprintln!("correct");
        }
    }

    Ok(())
}
