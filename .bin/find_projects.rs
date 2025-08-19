//! This script searches for projects with `.git` or `.hg` directories starting
//! from a given base directory. If no base directory is provided, it starts
//! from the current directory.
//!
//! # Compilation
//! To compile this script with optimizations enabled:
//! ```sh
//! rustc -O find_projects.rs
//! ```
use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::sync::mpsc;
use std::thread;

fn search_projects(base: &Path, sender: mpsc::Sender<PathBuf>) {
    let mut stack = Vec::from([base.to_path_buf()]);

    while let Some(path) = stack.pop() {
        let Ok(entries) = fs::read_dir(&path) else {
            continue;
        };
        for entry in entries {
            let Ok(entry) = entry else { continue };
            let path = entry.path();
            if path.is_dir() {
                if path.join(".git").exists() || path.join(".hg").exists() {
                    sender.send(path).unwrap();
                } else {
                    stack.push(path);
                }
            }
        }
    }
}

fn main() {
    let base = if let Some(path) = env::args().nth(1) {
        PathBuf::from(path)
    } else {
        env::current_dir().expect("Failed to get current directory")
    };

    thread::scope(|s| {
        let (sender, receiver) = mpsc::channel();
        s.spawn(|| search_projects(&base, sender));

        for project in receiver {
            println!("{}", project.strip_prefix(&base).unwrap().display());
        }
    });
}
