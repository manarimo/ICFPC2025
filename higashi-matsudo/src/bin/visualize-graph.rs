use std::path::Path;

use higashi_matsudo::{Problem, draw::draw_graph};
use rayon::iter::{IntoParallelIterator, ParallelIterator};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn main() -> Result<()> {
    // ../graph-dump/{probem}/{id}.json を列挙する
    let graph_dump_dir = Path::new("../graph-dump");
    let output_dir = graph_dump_dir.join("images");
    let problems = [
        Problem::Probatio,
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

    let mut list = vec![];
    for problem in problems {
        let path = graph_dump_dir.join(problem.to_str());
        let output_path = output_dir.join(problem.to_str());
        std::fs::create_dir_all(&output_path)?;
        let paths = std::fs::read_dir(path)?;
        for (i, path) in paths.enumerate() {
            let path = path?;
            let path = path.path();
            let out = output_path.join(format!("{}_{:03}.png", problem.to_str(), i));
            list.push((path, out));
        }
    }

    list.into_par_iter().for_each(|(path, out)| {
        draw_graph(path, out).expect("failed to draw graph");
    });
    Ok(())
}
