use higashi_matsudo::draw::draw_graph;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<String>>();
    draw_graph(&args[1], &args[2])?;
    Ok(())
}
