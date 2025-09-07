use std::{fs::read_to_string, path::Path};

use higashi_matsudo::{ApiClient, BackendType, GuessRequestMap, Problem};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

#[tokio::main]
async fn main() -> Result<()> {
    let backend_type = BackendType::Mock;
    let client = ApiClient::new(backend_type)?;

    let problems = [
        Problem::Primus,
        Problem::Secundus,
        Problem::Tertius,
        Problem::Quartus,
        Problem::Quintus,
        Problem::Aleph,
        Problem::Beth,
        Problem::Gimel,
        Problem::Daleth,
        Problem::He,
        Problem::Vau,
        Problem::Zain,
        Problem::Hhet,
        Problem::Teth,
        Problem::Iod,
    ];
    loop {
        for problem in problems {
            let path = Path::new("../graph-dump").join(problem.to_str());
            let files = std::fs::read_dir(path)?;
            for file in files {
                let file = file?;
                let file = file.path();
                eprintln!("file={}", file.display());
                let json = serde_json::from_str::<GuessRequestMap>(&read_to_string(file)?)?;

                client.select(problem).await?;
                let correct = client.guess(&json).await?;
                if correct {
                    eprintln!("correct");
                    return Ok(());
                }
            }
        }
    }
}
