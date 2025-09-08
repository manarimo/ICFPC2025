use std::time::Instant;

use higashi_matsudo::{ApiClient, BackendType, Event, ExploreQuery, Problem, graph::Node};
use rand::Rng;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

const NONE_LABEL: u8 = 10;

#[tokio::main]
async fn main() -> Result<()> {
    let mut rng = rand::rng();
    let backend_type = BackendType::Mock;
    let client = ApiClient::new(backend_type)?;

    let problems = [Problem::Primus, Problem::Beth, Problem::Vau];

    for problem in problems {
        for i in 0..3 {
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

    // 複数回リスタート + 焼きなまし + 改善降下
    let total_time_limit = match problem {
        Problem::Primus => 3.0_f64,
        Problem::Beth => 120.0_f64,
        Problem::Vau => 180.0_f64,
        _ => 10.0_f64,
    };
    let total_start = Instant::now();

    let mut global_best_cost = i64::MAX;
    let mut global_elapsed = 0.0_f64;

    while total_start.elapsed().as_secs_f64() < total_time_limit && global_best_cost > 0 {
        // 初期解
        let mut assign = vec![0; nodes.len()];
        for i in 0..nodes.len() {
            assign[i] = rng.random_range(0..n);
        }

        let local_limit = 0.5_f64;
        let start = Instant::now();
        let mut cur_cost = calc_cost(&assign, &nodes, n, l);
        let mut best_cost = cur_cost;

        // 温度スケジュール（線形）
        let t0 = (cur_cost.max(1) as f64).max(10.0);
        let t1 = 1e-3_f64;

        // 焼きなまし本体
        while start.elapsed().as_secs_f64() < local_limit && best_cost > 0 {
            let progress = start.elapsed().as_secs_f64() / local_limit;
            let t = t0 + (t1 - t0) * progress;

            // 近傍生成: 70% スワップ, 30% 再割当て
            let mut next_assign = assign.clone();
            if rng.random::<f64>() < 0.7 {
                let i = rng.random_range(0..nodes.len());
                let mut j = rng.random_range(0..nodes.len());
                if i == j {
                    j = (j + 1) % nodes.len();
                }
                next_assign.swap(i, j);
            } else {
                let i = rng.random_range(0..nodes.len());
                let to = rng.random_range(0..n);
                next_assign[i] = to;
            }

            let next_cost = calc_cost(&next_assign, &nodes, n, l);
            let delta = (cur_cost - next_cost) as f64;
            if delta >= 0.0 || rng.random::<f64>() < (delta / t).exp() {
                assign = next_assign;
                cur_cost = next_cost;
                if cur_cost < best_cost {
                    best_cost = cur_cost;
                }
            }
        }

        // 改善降下（確率受理なしのランダム近傍で末広がりの改善）
        let improve_trials = 5000;
        for _ in 0..improve_trials {
            let mut next_assign = assign.clone();
            if rng.random::<f64>() < 0.7 {
                let i = rng.random_range(0..nodes.len());
                let mut j = rng.random_range(0..nodes.len());
                if i == j {
                    j = (j + 1) % nodes.len();
                }
                next_assign.swap(i, j);
            } else {
                let i = rng.random_range(0..nodes.len());
                let to = rng.random_range(0..n);
                next_assign[i] = to;
            }
            let next_cost = calc_cost(&next_assign, &nodes, n, l);
            if next_cost < cur_cost {
                assign = next_assign;
                cur_cost = next_cost;
                if cur_cost < best_cost {
                    best_cost = cur_cost;
                }
            }
        }

        if best_cost < global_best_cost {
            global_best_cost = best_cost;
            global_elapsed = total_start.elapsed().as_secs_f64();
        }

        // 時間が余っており、改善余地がありそうなら別のリスタートへ
    }

    eprintln!(
        "anneal: best_cost={}, elapsed={:.3}s",
        global_best_cost, global_elapsed
    );

    Ok(())
}

fn calc_cost(assign: &[usize], nodes: &[Node], n: usize, l: usize) -> i64 {
    let g = n / l;
    assert_eq!(n % l, 0);

    let mut cost = 0;
    let mut vertex = vec![vec![]; n];
    let mut group = vec![vec![]; g];
    for i in 0..nodes.len() {
        vertex[assign[i]].push(i);
        group[assign[i] % g].push(i);
    }

    // 同じグループ内に異なるラベルのやつが入ってしまっている
    for group in &group {
        for &i in group {
            for &j in group {
                if nodes[i].label != nodes[j].label {
                    cost += 1;
                }
            }
        }
    }

    // 同じグループのノードから同じドアを通って到達できるノードのラベルが異なる
    for group in &group {
        for &i in group {
            for &j in group {
                for d in 0..6 {
                    if let (Some(i), Some(j)) = (nodes[i].neighbors[d], nodes[j].neighbors[d])
                        && nodes[i].label != nodes[j].label
                    {
                        cost += 1;
                    }
                }
            }
        }
    }

    // 同じvertexから同じドアを通って到達できるvertexのラベルが異なる
    for vertex in &vertex {
        for &i in vertex {
            for &j in vertex {
                for d in 0..6 {
                    if let (Some(i), Some(j)) = (nodes[i].neighbors[d], nodes[j].neighbors[d])
                        && assign[i] != assign[j]
                    {
                        cost += 1;
                    }
                }
            }
        }
    }

    cost
}
