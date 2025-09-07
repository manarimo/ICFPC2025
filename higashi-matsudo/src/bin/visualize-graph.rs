use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    path::Path,
};

use graphviz_rust::{
    cmd::{CommandArg, Format, Layout},
    exec_dot,
};
use higashi_matsudo::{GuessRequestMap, Problem};
use petgraph::{
    Graph,
    dot::{Config, Dot},
    graph::{NodeIndex, UnGraph},
};
use rand::Rng;
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

fn draw_graph(path: impl AsRef<Path>, out: impl AsRef<Path>) -> Result<()> {
    let file = std::fs::read_to_string(path)?;
    let map: GuessRequestMap = serde_json::from_str(&file)?;
    let n = map.rooms.len();
    let mut graph = vec![[0; 6]; n];

    for connection in map.connections {
        graph[connection.from.room][connection.from.door] = connection.to.room;
        graph[connection.to.room][connection.to.door] = connection.from.room;
    }

    let mut groups = BTreeMap::new();
    for i in 0..n {
        let hash = hash(i, &map.rooms, &graph);
        groups.entry(hash).or_insert(vec![]).push(i);
    }

    let groups = groups.into_values().collect::<Vec<Vec<usize>>>();
    let layer_counts = groups
        .iter()
        .map(|group| group.len())
        .collect::<Vec<usize>>();
    let max_layer_count = layer_counts.iter().max().expect("no layer counts");
    let min_layer_count = layer_counts.iter().min().expect("no layer counts");
    assert_eq!(max_layer_count, min_layer_count);

    eprintln!("groups={:?}", groups);
    let groups = optimize_layers(groups, &graph);
    let groups = optimize_groups(groups, &graph);

    let mut g: UnGraph<usize, ()> = Graph::new_undirected();
    let mut vertices = vec![];
    for i in 0..n {
        vertices.push(g.add_node(i));
    }

    let mut edges = BTreeSet::new();
    for i in 0..n {
        for door in 0..6 {
            let next = graph[i][door];
            if i >= next {
                continue;
            }
            edges.insert((i, next));
        }
    }

    for (i, next) in edges {
        g.add_edge(vertices[i], vertices[next], ());
    }

    let mut pos: HashMap<NodeIndex, (f32, f32)> = HashMap::new();
    for (group_label, group) in groups.iter().enumerate() {
        for (order, &i) in group.iter().enumerate() {
            pos.insert(vertices[i], (group_label as f32 * 5., order as f32 * 5.));
        }
    }

    let mut fill: HashMap<NodeIndex, &str> = HashMap::new();
    for i in 0..n {
        match map.rooms[i] {
            0 => {
                fill.insert(vertices[i], "red");
            }
            1 => {
                fill.insert(vertices[i], "blue");
            }
            2 => {
                fill.insert(vertices[i], "green");
            }
            3 => {
                fill.insert(vertices[i], "gray");
            }
            _ => unreachable!(),
        }
    }

    let node_attr = |_g, (idx, _w)| {
        let (x, y) = pos[&idx];
        let color = fill.get(&idx).copied().unwrap_or("white");
        format!(
            r#"shape=circle, width=0.5, height=0.5, pos="{:.2},{:.2}!", style=filled, fillcolor="{}", color="black""#,
            x, y, color
        )
    };

    let dot = Dot::with_attr_getters(
        &g,
        &[Config::EdgeNoLabel],
        &|_g, _e| String::new(),
        &node_attr,
    );

    exec_dot(
        format!("{:?}", dot),
        vec![
            CommandArg::Layout(Layout::Fdp),
            CommandArg::Custom("-n".into()),
            CommandArg::Format(Format::Png),
            CommandArg::Output(out.as_ref().to_string_lossy().to_string()),
        ],
    )?;
    Ok(())
}

fn optimize_groups(mut groups: Vec<Vec<usize>>, graph: &[[usize; 6]]) -> Vec<Vec<usize>> {
    let mut rng = rand::rng();

    const ITERATIONS: usize = 1_000_000;
    const INITIAL_TEMP: f64 = 1.0;
    const TERMINAL_TEMP: f64 = 1e-3;
    let alpha: f64 = -(TERMINAL_TEMP / INITIAL_TEMP).ln();

    let mut current_cost: i64 = calc_group_cost(&groups, graph) as i64;
    let mut best_cost: i64 = current_cost;
    let mut best_groups = groups.clone();
    let mut temperature = INITIAL_TEMP;

    for t in 0..ITERATIONS {
        let i = rng.random_range(0..groups.len());
        let j = rng.random_range(0..groups.len());
        if i == j {
            let progress = (t + 1) as f64 / ITERATIONS as f64;
            temperature = INITIAL_TEMP * (-alpha * progress).exp();
            continue;
        }

        groups.swap(i, j);
        let new_cost: i64 = calc_group_cost(&groups, graph) as i64;
        let delta: i64 = new_cost - current_cost;

        let accept = if delta <= 0 {
            true
        } else {
            let prob = (-(delta as f64) / temperature).exp();
            rng.random_range(0.0..1.0) < prob
        };

        if accept {
            current_cost = new_cost;
            if current_cost < best_cost {
                best_cost = current_cost;
                best_groups = groups.clone();
                eprintln!("group best_cost={}", best_cost);
            }
        } else {
            groups.swap(i, j);
        }

        let progress = (t + 1) as f64 / ITERATIONS as f64;
        temperature = INITIAL_TEMP * (-alpha * progress).exp();
    }

    eprintln!("optimized group best_cost={}", best_cost);
    best_groups
}

fn optimize_layers(groups: Vec<Vec<usize>>, graph: &[[usize; 6]]) -> Vec<Vec<usize>> {
    let n = graph.len();
    let mut layers = vec![0; n];
    for group in &groups {
        for (layer, &i) in group.iter().enumerate() {
            layers[i] = layer;
        }
    }

    const ITERATIONS: usize = 1_000_000;
    const INITIAL_TEMP: f64 = 1.0;
    const TERMINAL_TEMP: f64 = 1e-3;
    let alpha: f64 = -(TERMINAL_TEMP / INITIAL_TEMP).ln(); // T = T0 * exp(-alpha * t)

    let m = groups.len();
    let mut rng = rand::rng();

    let mut current_cost = calc_layer_cost(&layers, graph);
    let mut best_cost = current_cost;
    let mut best_layers = layers.clone();
    let mut temperature = INITIAL_TEMP;

    for t in 0..ITERATIONS {
        let selected_layer_id = rng.random_range(0..m);
        let i_idx = rng.random_range(0..groups[selected_layer_id].len());
        let j_idx = rng.random_range(0..groups[selected_layer_id].len());
        if i_idx == j_idx {
            let progress = (t + 1) as f64 / ITERATIONS as f64;
            temperature = INITIAL_TEMP * (-alpha * progress).exp();
            continue;
        }

        let i = groups[selected_layer_id][i_idx];
        let j = groups[selected_layer_id][j_idx];
        assert_ne!(i, j);

        layers.swap(i, j);
        let new_cost = calc_layer_cost(&layers, graph);

        let delta = new_cost - current_cost;
        let accept = if delta <= 0 {
            true
        } else {
            let prob = (-(delta as f64) / temperature).exp();
            rng.random_range(0.0..1.0) < prob
        };

        if accept {
            current_cost = new_cost;
            if current_cost < best_cost {
                eprintln!("best_cost={}", best_cost);
                best_cost = current_cost;
                best_layers = layers.clone();
            }
        } else {
            layers.swap(i, j); // revert
        }

        let progress = (t + 1) as f64 / ITERATIONS as f64;
        temperature = INITIAL_TEMP * (-alpha * progress).exp();
    }

    let groups = groups
        .into_iter()
        .map(|group| {
            let mut group = group
                .iter()
                .map(|&i| (best_layers[i], i))
                .collect::<Vec<_>>();
            group.sort();
            group.into_iter().map(|(_, i)| i).collect::<Vec<_>>()
        })
        .collect::<Vec<Vec<usize>>>();

    eprintln!("optimized best_cost={}", best_cost);
    groups
}

fn calc_layer_cost(layers: &[usize], graph: &[[usize; 6]]) -> i64 {
    let n = graph.len();
    let mut cost = 0;
    for i in 0..n {
        for door in 0..6 {
            let next = graph[i][door];
            if layers[i] != layers[next] {
                cost += 1;
            }
        }
    }
    cost
}

fn calc_group_cost(groups: &[Vec<usize>], graph: &[[usize; 6]]) -> usize {
    let n = graph.len();
    let mut group_labels = vec![0; n];
    for (group_label, group) in groups.iter().enumerate() {
        for &i in group {
            group_labels[i] = group_label;
        }
    }

    let mut cost = 0;
    for i in 0..n {
        let pos = group_labels[i];
        for door in 0..6 {
            let next = graph[i][door];
            let distance = pos.abs_diff(group_labels[next]);
            cost += distance;
        }
    }
    cost
}

fn hash(node_id: usize, labels: &[u8], graph: &[[usize; 6]]) -> u128 {
    let mut hash = labels[node_id] as u128;
    for door1 in 0..6 {
        let next = graph[node_id][door1];
        hash <<= 2;
        hash |= labels[next] as u128;
        for door2 in 0..6 {
            let next = graph[next][door2];
            hash <<= 2;
            hash |= labels[next] as u128;
        }
    }
    hash
}
