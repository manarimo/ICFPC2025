use std::{
    collections::{BTreeMap, BTreeSet, VecDeque},
    fs::File,
    io::Write as _,
    time::{SystemTime, UNIX_EPOCH},
};

use higashi_matsudo::{
    ApiClient, BackendType, Connection, Event, ExploreQuery, GuessRequestMap, Problem, Vertex,
    union_find::UnionFind,
};
use rand::Rng;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let backend_type = BackendType::Official;
    let client = ApiClient::new(backend_type)?;

    loop {
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

        for problem in problems {
            eprintln!("problem={}", problem.to_str());
            client.select(problem).await?;

            let n = problem.problem_size();
            let mut uf = UnionFind::new(n * 1000);
            let mut nodes = vec![];

            let mut plan = vec![];
            for i in 0.. {
                trial(&mut rng, &mut nodes, n, &client, plan, &mut uf).await?;
                match construct_door_open_plan(&nodes, &mut uf) {
                    Some(new_plan) => {
                        eprintln!("new plan found, i={i}");
                        plan = new_plan;
                    }
                    None => break,
                }
            }

            let guess = construct_guess(&nodes, &mut uf, n);

            let correct = client.guess(&guess).await?;
            if !correct {
                eprintln!("incorrect guess");
                return Err("incorrect guess".into());
            }

            save_guess(&guess, problem, backend_type)?;
        }
    }
}

async fn trial(
    rng: &mut impl Rng,
    nodes: &mut Vec<Node>,
    problem_size: usize,
    client: &ApiClient,
    mut plan: Vec<ExploreQuery>,
    uf: &mut UnionFind,
) -> Result<()> {
    while plan.len() < problem_size * 6 {
        plan.push(ExploreQuery::open(rng.random_range(0..6)));
    }

    let events = client.explore(&plan).await?;
    match events[0] {
        Event::VisitRoom { label } => {
            nodes.push(Node::new(label));
        }
        _ => unreachable!(),
    }

    let mut cur = uf.find(0);
    for event in events.into_iter().skip(1) {
        match event {
            Event::VisitRoom { label } => {
                nodes[cur].label = label;
            }
            Event::OpenDoor { door } => match nodes[cur].neighbors[door] {
                Some(next) => {
                    let next = uf.find(next);
                    nodes[cur].neighbors[door] = Some(next);
                    cur = next;
                }
                None => {
                    let next = nodes.len();
                    nodes.push(Node::new(10));
                    nodes[cur].neighbors[door] = Some(next);
                    cur = next;
                }
            },
            Event::Overwrite { .. } => unreachable!(),
        }
    }

    for pos in 0..(plan.len() / 2) {
        // generate new plan
        let last_node_id = reach(&nodes, &plan[0..pos], uf);
        let mut new_plan = plan.clone();
        new_plan.insert(
            pos,
            ExploreQuery::Charcoal {
                label: find_different_label(nodes[last_node_id].label),
            },
        );

        let events = client.explore(&new_plan).await?;

        // find marked nodes
        let mut cur = uf.find(0);
        let mut mark = BTreeSet::new();
        for (i, &event) in events.iter().enumerate() {
            match event {
                Event::VisitRoom { label } => {
                    if label != nodes[cur].label {
                        mark.insert(cur);
                    }
                }
                Event::OpenDoor { door } => match nodes[cur].neighbors[door] {
                    Some(next) => {
                        let next = uf.find(next);
                        cur = next;
                    }
                    None => unreachable!(
                        "closed door found when marking cur={cur} door={door} plan={:?} new_plan={:?} events={:?} i={i}",
                        plan, new_plan, events,
                    ),
                },
                Event::Overwrite { label } => {
                    if label != nodes[cur].label {
                        mark.insert(cur);
                    }
                }
            }
        }

        assert!(mark.len() > 0, "{:?}", mark);

        let mut queue = VecDeque::new();
        queue.push_back(mark);

        // sweep
        while let Some(mark) = queue.pop_front() {
            let &representative_id = mark.iter().next().expect("no mark");

            for node_id in mark {
                uf.unite(node_id, representative_id);
            }

            let mut groups = vec![vec![]; nodes.len()];
            for node_id in 0..nodes.len() {
                groups[uf.find(node_id)].push(node_id);
            }

            // グループ内でドアの先を統一する
            for group in groups {
                for door in 0..6 {
                    let mut next_mark = BTreeSet::new();
                    for &node_id in &group {
                        if let Some(next) = nodes[node_id].neighbors[door] {
                            next_mark.insert(next);
                        }
                    }

                    if next_mark.len() == 0 {
                        continue;
                    }

                    let next_min_id = *next_mark.iter().next().expect("no mark");
                    let next_root_id = uf.find(next_min_id);
                    for &next_marked in next_mark.iter() {
                        uf.unite(next_marked, next_root_id);
                    }

                    let next_root_id = uf.find(next_root_id);
                    for &node_id in &group {
                        nodes[node_id].neighbors[door] = Some(next_root_id);
                    }

                    if next_mark.len() > 1 {
                        queue.push_back(next_mark);
                    }
                }
            }
        }

        // validate groups
        let mut groups = vec![vec![]; nodes.len()];
        for node_id in 0..nodes.len() {
            groups[uf.find(node_id)].push(node_id);
        }
        for group in groups {
            for door in 0..6 {
                let all_same = group.iter().all(|&node_id| {
                    nodes[node_id].neighbors[door] == nodes[group[0]].neighbors[door]
                });
                assert!(all_same);
            }
        }
    }

    Ok(())
}

#[derive(Debug, Clone, Copy)]
struct Node {
    label: u8,
    neighbors: [Option<usize>; 6],
}

impl Node {
    fn new(label: u8) -> Self {
        Self {
            label,
            neighbors: [None; 6],
        }
    }
}

fn reach(nodes: &[Node], plan: &[ExploreQuery], uf: &mut UnionFind) -> usize {
    let mut cur = uf.find(0);
    for query in plan {
        match query {
            ExploreQuery::Open { door } => {
                cur = nodes[cur].neighbors[*door as usize].expect("door is not open");
                cur = uf.find(cur);
            }
            ExploreQuery::Charcoal { .. } => unreachable!(),
        }
    }
    cur
}

fn find_different_label(label: u8) -> u8 {
    (0..).find(|&x| x != label).expect("unreachable")
}

fn save_guess(guess: &GuessRequestMap, problem: Problem, backend_type: BackendType) -> Result<()> {
    let unix_time = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("failed to get unix time")
        .as_secs();

    let dir = format!("../{}/{}", backend_type.directory(), problem.to_str());
    std::fs::create_dir_all(&dir)?;
    let file_name = format!("{dir}/{unix_time}.json");
    let mut file = File::create(file_name)?;
    file.write_all(
        serde_json::to_string_pretty(&guess)
            .expect("failed to serialize guess")
            .as_bytes(),
    )?;

    Ok(())
}

fn construct_guess(nodes: &[Node], uf: &mut UnionFind, n: usize) -> GuessRequestMap {
    let mut queue = VecDeque::new();
    queue.push_back(uf.find(0));
    let mut vis = vec![false; nodes.len()];
    vis[uf.find(0)] = true;
    while let Some(v) = queue.pop_front() {
        for door in 0..6 {
            let next = nodes[v].neighbors[door].expect("closed door found");
            let next = uf.find(next);
            if !vis[next] {
                vis[next] = true;
                queue.push_back(next);
            }
        }
    }

    let mut map = BTreeMap::new();
    for i in 0..nodes.len() {
        let i = uf.find(i);
        if vis[i] && !map.contains_key(&i) {
            let index = map.len();
            map.insert(i, index);
        }
    }
    assert_eq!(map.len(), n);

    let mut labels = vec![0; n];
    let mut edges = vec![];
    for i in 0..nodes.len() {
        let i = uf.find(i);
        let Some(&index) = map.get(&i) else {
            continue;
        };
        labels[index] = nodes[i].label;
        for door in 0..6 {
            let next = nodes[i].neighbors[door].expect("closed door found");
            let next = uf.find(next);
            let next_index = *map.get(&next).expect("unindexed node found");

            let Some(reverse_door) = nodes[next]
                .neighbors
                .iter()
                .enumerate()
                .map(|(reverse_door, &reverse_node)| {
                    let reverse_node = reverse_node.expect("closed door found");
                    let reverse_node = uf.find(reverse_node);
                    (reverse_door, reverse_node)
                })
                .find(|&(_, reverse_node)| reverse_node == i)
                .map(|(reverse_door, _)| reverse_door)
            else {
                eprintln!("reverse door not found, i={i}, next={next}");
                eprintln!("uf.find(i)={}", uf.find(i));
                eprintln!("uf.find(next)={}", uf.find(next));
                eprintln!("nodes[i]={:?}", nodes[i]);
                eprintln!("nodes[next]={:?}", nodes[next]);

                for (door, next) in nodes[i].neighbors.iter().enumerate() {
                    let next = next.expect("closed door found");
                    eprintln!("nodes[i][{door}]={next} {}", uf.find(next));
                }
                for (door, next) in nodes[next].neighbors.iter().enumerate() {
                    let next = next.expect("closed door found");
                    eprintln!("nodes[next][{door}]={next} {}", uf.find(next));
                }
                panic!("reverse door not found");
            };

            let v1 = (index, door);
            let v2 = (next_index, reverse_door);

            let (from, to) = (v1.min(v2), v1.max(v2));
            edges.push((from, to));
        }
    }

    edges.sort();
    edges.dedup();

    let starting_room = *map.get(&uf.find(0)).expect("starting room not found");

    GuessRequestMap {
        rooms: labels,
        starting_room,
        connections: edges
            .into_iter()
            .map(|(from, to)| Connection {
                from: Vertex {
                    room: from.0,
                    door: from.1,
                },
                to: Vertex {
                    room: to.0,
                    door: to.1,
                },
            })
            .collect(),
    }
}

fn construct_door_open_plan(nodes: &[Node], uf: &mut UnionFind) -> Option<Vec<ExploreQuery>> {
    let mut queue = VecDeque::new();
    queue.push_back(uf.find(0));

    let mut found = None;
    let mut prev = vec![None; nodes.len()];
    while let Some(v) = queue.pop_front() {
        let v = uf.find(v);
        for door in 0..6 {
            match nodes[v].neighbors[door] {
                Some(next) => {
                    if prev[next].is_none() {
                        prev[next] = Some((v, door));
                        queue.push_back(next);
                    }
                }
                None => {
                    found = Some((v, door));
                }
            }
        }
    }

    let (target, door) = found?;

    let mut cur = target;
    let mut plan = vec![];
    while cur != uf.find(0)
        && let Some((prev, door)) = prev[cur]
    {
        plan.push(ExploreQuery::open(door));
        cur = prev;
    }
    plan.reverse();
    plan.push(ExploreQuery::open(door));

    Some(plan)
}
