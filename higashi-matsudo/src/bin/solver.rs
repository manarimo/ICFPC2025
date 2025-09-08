use std::{
    collections::{BTreeSet, VecDeque},
    time::{Instant, SystemTime},
};

use higashi_matsudo::{
    ApiClient, BackendType, Event, ExploreQuery, Problem, graph::Node, union_find::UnionFind,
};
use rand::Rng;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

const NONE_LABEL: u8 = 10;

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let backend_type = BackendType::Mock;
    let client = ApiClient::new(backend_type)?;

    let problems = [Problem::Primus];

    for problem in problems {
        for i in 0..10 {
            eprintln!("problem={}, testcase={i}", problem.to_str());
            client.select(problem).await?;

            solve(&mut rng, &client, problem).await?;
        }
    }
    Ok(())
}

async fn solve(rng: &mut impl Rng, client: &ApiClient, problem: Problem) -> Result<()> {
    let n = problem.problem_size();
    let l = problem.layer_count();
    let g = n / l;
    assert_eq!(n % l, 0);

    let mut nodes = vec![];

    let mut plan = vec![];
    for _ in 0..(6 * n) {
        plan.push(ExploreQuery::open(rng.random_range(0..6)));
    }
    let first_plans = [plan];
    let batch = client.explore(&first_plans).await?;
    match batch[0][0] {
        Event::VisitRoom { label } => {
            nodes.push(Node::new(label));
        }
        _ => unreachable!(),
    }

    let first_events = &batch[0];
    let mut cur_room = 0;
    for &event in first_events {
        match event {
            Event::VisitRoom { label } => {
                nodes[cur_room].label = label;
            }
            Event::OpenDoor { door } => match nodes[cur_room].neighbors[door] {
                Some(next) => {
                    cur_room = next;
                }
                None => {
                    let next = nodes.len();
                    nodes.push(Node::new(NONE_LABEL));
                    nodes[cur_room].neighbors[door] = Some(next);
                    cur_room = next;
                }
            },
            Event::Overwrite { .. } => {}
        }
    }

    let mut assign = vec![0; nodes.len()];
    for i in 0..nodes.len() {
        assign[i] = rng.random_range(0..g);
    }

    // 近傍とコストの増分を高速に評価するための前処理
    let node_labels: Vec<usize> = nodes.iter().map(|n| n.label as usize).collect();
    let mut neighbor_labels: Vec<[Option<usize>; 6]> = vec![[None; 6]; nodes.len()];
    for i in 0..nodes.len() {
        for d in 0..6 {
            if let Some(j) = nodes[i].neighbors[d] {
                neighbor_labels[i][d] = Some(nodes[j].label as usize);
            }
        }
    }

    struct AssignState {
        assign: Vec<usize>,
        group_size: Vec<i32>,
        group_label_count: Vec<[i32; 4]>,
        group_next_label_count: Vec<[[i32; 4]; 6]>,
        node_labels: Vec<usize>,
        neighbor_labels: Vec<[Option<usize>; 6]>,
        cur_cost: i64,
    }

    impl AssignState {
        fn new(
            assign: Vec<usize>,
            node_labels: Vec<usize>,
            neighbor_labels: Vec<[Option<usize>; 6]>,
            g: usize,
            nodes: &[Node],
        ) -> Self {
            let mut group_size = vec![0i32; g];
            let mut group_label_count = vec![[0i32; 4]; g];
            let mut group_next_label_count = vec![[[0i32; 4]; 6]; g];

            for (i, &grp) in assign.iter().enumerate() {
                group_size[grp] += 1;
                let lab = node_labels[i];
                group_label_count[grp][lab] += 1;
                for d in 0..6 {
                    if let Some(nlab) = neighbor_labels[i][d] {
                        group_next_label_count[grp][d][nlab] += 1;
                    }
                }
            }

            let cur_cost = cost(&assign, nodes, g);

            Self {
                assign,
                group_size,
                group_label_count,
                group_next_label_count,
                node_labels,
                neighbor_labels,
                cur_cost,
            }
        }

        fn contrib_from(size: i32, label_cnt: &[i32; 4], next_cnt: &[[i32; 4]; 6]) -> i64 {
            let size64 = size as i64;
            let max_label = *label_cnt.iter().max().unwrap_or(&0) as i64;
            let mut s = size64 - max_label;
            for d in 0..6 {
                let mx = *next_cnt[d].iter().max().unwrap_or(&0) as i64;
                let active = next_cnt[d].iter().map(|&v| v as i64).sum::<i64>();
                s += active - mx;
            }
            s
        }

        fn contrib(&self, gid: usize) -> i64 {
            Self::contrib_from(
                self.group_size[gid],
                &self.group_label_count[gid],
                &self.group_next_label_count[gid],
            )
        }

        fn delta_move(&self, idx: usize, to_group: usize) -> i64 {
            let from_group = self.assign[idx];
            if from_group == to_group {
                return 0;
            }

            let lab = self.node_labels[idx];

            // before
            let before = self.contrib(from_group) + self.contrib(to_group);

            // simulate updates for from_group
            let size_a = self.group_size[from_group] - 1;
            let mut label_a = self.group_label_count[from_group];
            label_a[lab] -= 1;
            let mut next_a = self.group_next_label_count[from_group];
            for d in 0..6 {
                if let Some(nlab) = self.neighbor_labels[idx][d] {
                    next_a[d][nlab] -= 1;
                }
            }

            // simulate updates for to_group
            let size_b = self.group_size[to_group] + 1;
            let mut label_b = self.group_label_count[to_group];
            label_b[lab] += 1;
            let mut next_b = self.group_next_label_count[to_group];
            for d in 0..6 {
                if let Some(nlab) = self.neighbor_labels[idx][d] {
                    next_b[d][nlab] += 1;
                }
            }

            let after = Self::contrib_from(size_a, &label_a, &next_a)
                + Self::contrib_from(size_b, &label_b, &next_b);

            after - before
        }

        fn apply_move(&mut self, idx: usize, to_group: usize) {
            let from_group = self.assign[idx];
            if from_group == to_group {
                return;
            }

            let lab = self.node_labels[idx];
            self.group_size[from_group] -= 1;
            self.group_label_count[from_group][lab] -= 1;
            for d in 0..6 {
                if let Some(nlab) = self.neighbor_labels[idx][d] {
                    self.group_next_label_count[from_group][d][nlab] -= 1;
                }
            }

            self.group_size[to_group] += 1;
            self.group_label_count[to_group][lab] += 1;
            for d in 0..6 {
                if let Some(nlab) = self.neighbor_labels[idx][d] {
                    self.group_next_label_count[to_group][d][nlab] += 1;
                }
            }

            self.assign[idx] = to_group;
        }
    }

    // 焼きなましで assign を最適化（増分計算 + 最良グループ探索）
    let time_limit_ms: u128 = 3000; // ms 固定
    let start = Instant::now();

    let mut state = AssignState::new(assign, node_labels, neighbor_labels, g, &nodes);
    let mut best_assign = state.assign.clone();
    let mut best_cost = state.cur_cost;

    // 強力な貪欲改善（時間の最大50% or 収束まで）
    let greedy_deadline = (time_limit_ms / 2) as u128;
    loop {
        if start.elapsed().as_millis() >= greedy_deadline {
            break;
        }
        let mut improved = false;
        for i in 0..state.assign.len() {
            if start.elapsed().as_millis() >= greedy_deadline {
                break;
            }
            let from_group = state.assign[i];
            let mut best_delta = 0i64;
            let mut best_to = from_group;
            for to in 0..g {
                if to == from_group {
                    continue;
                }
                let d = state.delta_move(i, to);
                if d < best_delta {
                    best_delta = d;
                    best_to = to;
                }
            }
            if best_to != from_group {
                state.cur_cost += best_delta;
                state.apply_move(i, best_to);
                if state.cur_cost < best_cost {
                    best_cost = state.cur_cost;
                    best_assign.copy_from_slice(&state.assign);
                }
                improved = true;
            }
        }
        if !improved {
            break;
        }
    }

    let t0 = (best_cost.max(1)) as f64;
    let t1 = 1e-3_f64;

    while start.elapsed().as_millis() < time_limit_ms {
        let elapsed = start.elapsed().as_micros() as f64;
        let limit = (time_limit_ms as f64) * 1000.0;
        let progress = (elapsed / limit).min(1.0);
        // 幾何冷却
        let temp = t0 * (t1 / t0).powf(progress);

        let i = rng.random_range(0..state.assign.len());
        let from_group = state.assign[i];

        // 最良の行き先グループを探索
        let mut best_delta = i64::MAX;
        let mut best_to = from_group;
        for to in 0..g {
            if to == from_group {
                continue;
            }
            let d = state.delta_move(i, to);
            if d < best_delta {
                best_delta = d;
                best_to = to;
            }
        }

        let accept = if best_delta <= 0 {
            true
        } else {
            let prob = (-(best_delta as f64) / temp).exp();
            rng.random::<f64>() < prob
        };

        if accept && best_to != from_group {
            state.cur_cost += best_delta;
            state.apply_move(i, best_to);
            if state.cur_cost < best_cost {
                best_cost = state.cur_cost;
                best_assign.copy_from_slice(&state.assign);
            }
        }
    }

    // 最良解を反映（現状はログのみ）
    eprintln!("anneal_cost={}", best_cost);

    let mut groups = vec![vec![]; g];
    for i in 0..nodes.len() {
        groups[best_assign[i]].push(i);
    }

    assign_to_map(&best_assign, &mut nodes, g, l, rng);

    Ok(())
}

fn assign_to_map(
    assign: &[usize],
    nodes: &mut [Node],
    g: usize,
    l: usize,
    rng: &mut impl Rng,
) -> Vec<Vec<usize>> {
    let mut groups = vec![vec![]; g];
    for i in 0..nodes.len() {
        groups[assign[i]].push(i);
    }

    let mut uf = UnionFind::new(nodes.len());
    while let Some(id) = groups
        .iter()
        .enumerate()
        .find(|(_, g)| g.len() > l)
        .map(|(i, _)| i)
    {
        eprintln!("groups={:?}", groups);
        let i = rng.random_range(0..groups[id].len());
        let j = rng.random_range(0..groups[id].len());
        if i == j {
            continue;
        }

        let mut q = VecDeque::new();
        let mut set = BTreeSet::new();
        set.insert(groups[id][i]);
        set.insert(groups[id][j]);
        q.push_back(set);

        while let Some(set) = q.pop_front() {
            let id = *set.iter().next().expect("no id");
            for &i in &set {
                uf.unite(i, id);
            }
            for door in 0..6 {
                let mut next_set = BTreeSet::new();
                for &i in &set {
                    if let Some(next) = nodes[i].neighbors[door] {
                        next_set.insert(uf.find(next));
                    }
                }
                for &i in &set {
                    nodes[i].neighbors[door] = next_set.iter().next().copied();
                }

                if next_set.len() > 1 {
                    q.push_back(next_set);
                }
            }
        }

        groups = groups
            .into_iter()
            .map(|g| {
                let mut group = g.into_iter().map(|i| uf.find(i)).collect::<Vec<_>>();
                group.sort();
                group.dedup();
                group
            })
            .collect::<Vec<_>>();
    }

    todo!()
}

fn cost(assign: &[usize], nodes: &[Node], g: usize) -> i64 {
    let mut groups = vec![vec![]; g];
    for i in 0..nodes.len() {
        groups[assign[i]].push(i);
    }

    let mut cost = 0;
    for group in &groups {
        let mut label_count = [0; 4];
        for &i in group {
            label_count[nodes[i].label as usize] += 1;
        }

        let group_size = group.len() as i64;
        let max_count = *label_count.iter().max().expect("no label count");
        cost += group_size - max_count;
    }

    for group in &groups {
        for door in 0..6 {
            let mut next_label_count = [0; 4];
            let mut active = 0i64;
            for &i in group {
                if let Some(next) = nodes[i].neighbors[door] {
                    next_label_count[nodes[next].label as usize] += 1;
                    active += 1;
                }
            }

            let max_count = *next_label_count.iter().max().expect("no label count");
            cost += active - max_count;
        }
    }

    cost
}
