use std::collections::{BTreeMap, BTreeSet, VecDeque};

use crate::{Connection, GuessRequestMap, Vertex, union_find::UnionFind};

#[derive(Debug, Clone, Copy)]
pub struct Node {
    pub label: u8,
    pub neighbors: [Option<usize>; 6],
}

impl Node {
    pub fn new(label: u8) -> Self {
        Self {
            label,
            neighbors: [None; 6],
        }
    }
}
pub fn construct_guess(nodes: &[Node], uf: &mut UnionFind, n: usize) -> GuessRequestMap {
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
    let mut used_doors = BTreeSet::new();
    for i in 0..nodes.len() {
        let i = uf.find(i);
        let Some(&index) = map.get(&i) else {
            continue;
        };
        labels[index] = nodes[i].label;
        for door in 0..6 {
            if used_doors.contains(&(i, door)) {
                continue;
            }

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
                .filter(|&(reverse_door, _)| !used_doors.contains(&(next, reverse_door)))
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

            used_doors.insert((i, door));
            used_doors.insert((next, reverse_door));

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
