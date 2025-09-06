use std::collections::BTreeMap;

use higashi_matsudo::{ApiClient, BackendType, MultiSet};
use rand::Rng;

const SIX: u8 = 6;
const N: usize = 60;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn generate_random_plan(length: usize, rng: &mut impl Rng) -> Vec<u8> {
    (0..length).map(|_| rng.random_range(0..SIX)).collect()
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let client = ApiClient::new(BackendType::Mock)?;

    // 部屋の数
    let n = client.select("primus").await?;

    // 移動の履歴
    let a = generate_random_plan(n * 18, &mut rng);

    // 移動した部屋の色
    let b = client.explore(&a).await?;

    let mut nodes = vec![Node::new(); n];
    let mut groups = [vec![], vec![], vec![], vec![]];
    let mut remain_stack = (1..n).collect();

    nodes[0].color = Some(b[0]);
    groups[b[0]].push(0);

    let result = dfs(0, &mut groups, &mut remain_stack, &mut nodes, &a, &b[1..]);
    assert!(result, "a={:?}, b={:?}", a, b);

    Ok(())
}

type VertexID = usize;
type DoorID = u8;
type ColorID = usize;

#[derive(Clone)]
struct Node {
    color: Option<ColorID>,

    edges_by_door: BTreeMap<DoorID, VertexID>,
    undefined_edges: MultiSet<N>,
}
impl Node {
    fn new() -> Self {
        Self {
            color: None,
            edges_by_door: BTreeMap::new(),
            undefined_edges: MultiSet::new(),
        }
    }
}

fn dfs(
    v: usize,
    groups: &mut [Vec<VertexID>; 4],
    remain_stack: &mut Vec<VertexID>,
    nodes: &mut [Node],
    doors: &[DoorID],
    colors: &[ColorID],
) -> bool {
    if doors.is_empty() {
        return true;
    }

    assert_eq!(doors.len(), colors.len());
    let next_color = colors[0];
    let using_door = doors[0];

    // 既に確定した辺があるとき
    if let Some(&next_v) = nodes[v].edges_by_door.get(&using_door) {
        if nodes[next_v].color != Some(next_color) {
            return false;
        }

        return dfs(
            next_v,
            groups,
            remain_stack,
            nodes,
            &doors[1..],
            &colors[1..],
        );
    }

    if nodes[v].edges_by_door.contains_key(&using_door) {
        return false;
    }

    // 入ってくる未確定の辺を使う場合
    for next_v in nodes[v].undefined_edges.to_vec() {
        match nodes[next_v].color {
            Some(c) => {
                if c != next_color {
                    continue;
                }

                nodes[v].undefined_edges.remove(next_v);
                let existing = nodes[v].edges_by_door.insert(using_door, next_v);
                assert!(existing.is_none());

                if dfs(
                    next_v,
                    groups,
                    remain_stack,
                    nodes,
                    &doors[1..],
                    &colors[1..],
                ) {
                    return true;
                }

                nodes[v].undefined_edges.insert(next_v);
                let removed = nodes[v].edges_by_door.remove(&using_door);
                assert_eq!(removed, Some(next_v));
            }
            None => unreachable!(),
        }
    }

    // 既に色が確定している頂点にいくとき
    if nodes[v].undefined_edges.len() + nodes[v].edges_by_door.len() < 6 {
        for next_v in groups[next_color].clone() {
            if nodes[next_v].undefined_edges.len() + nodes[next_v].edges_by_door.len() >= 6 {
                continue;
            }

            nodes[v].edges_by_door.insert(using_door, next_v);
            nodes[next_v].undefined_edges.insert(v);

            if dfs(
                next_v,
                groups,
                remain_stack,
                nodes,
                &doors[1..],
                &colors[1..],
            ) {
                return true;
            }

            nodes[v].edges_by_door.remove(&using_door);
            nodes[next_v].undefined_edges.remove(v);
        }
    }

    // 完全新規の頂点にいくとき
    if let Some(&next_v) = remain_stack.last()
        && nodes[v].undefined_edges.len() + nodes[v].edges_by_door.len() < 6
        && nodes[next_v].undefined_edges.len() + nodes[next_v].edges_by_door.len() < 6
    {
        nodes[v].edges_by_door.insert(using_door, next_v);
        nodes[next_v].undefined_edges.insert(v);
        groups[next_color].push(next_v);
        assert!(nodes[next_v].color.is_none());
        nodes[next_v].color = Some(next_color);
        let last = remain_stack.pop();
        assert_eq!(last, Some(next_v));

        if dfs(
            next_v,
            groups,
            remain_stack,
            nodes,
            &doors[1..],
            &colors[1..],
        ) {
            return true;
        }

        let removed = nodes[v].edges_by_door.remove(&using_door);
        assert_eq!(removed, Some(next_v));
        nodes[next_v].undefined_edges.remove(v);
        let pop = groups[next_color].pop();
        assert_eq!(pop, Some(next_v));
        nodes[next_v].color = None;
        remain_stack.push(next_v);
    }

    false
}
