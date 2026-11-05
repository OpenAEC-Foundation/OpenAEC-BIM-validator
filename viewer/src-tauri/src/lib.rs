// BIM Validator desktop shell.
//
// On launch (release builds) this spawns the bundled headless Python server
// (FastAPI/uvicorn on 127.0.0.1:8000) as a child process and shuts it down
// when the app exits. In dev builds the server is expected to run separately
// (e.g. `uvicorn server.main:app`), matching the Vite dev workflow.

mod accounts;

use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::Manager;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

/// Holds the embedded server child process so it can be killed on exit.
struct ServerProcess(Mutex<Option<Child>>);

/// Spawn the bundled headless server. Returns None in dev builds or on failure.
fn spawn_server(app: &tauri::App) -> Option<Child> {
    if cfg!(debug_assertions) {
        log::info!("dev build: expecting Python server on http://127.0.0.1:8000");
        return None;
    }

    let resource_dir = match app.path().resource_dir() {
        Ok(dir) => dir,
        Err(e) => {
            log::error!("could not resolve resource dir: {e}");
            return None;
        }
    };

    let exe = resource_dir
        .join("server")
        .join("bim-validator-server.exe");
    if !exe.exists() {
        log::error!("bundled server not found at {exe:?}");
        return None;
    }

    let mut cmd = Command::new(&exe);
    if let Some(parent) = exe.parent() {
        cmd.current_dir(parent);
    }
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    match cmd.spawn() {
        Ok(child) => {
            log::info!("spawned embedded server: {exe:?}");
            Some(child)
        }
        Err(e) => {
            log::error!("failed to spawn embedded server: {e}");
            None
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            accounts::accounts_sign_in,
            accounts::accounts_get_user,
            accounts::accounts_sign_out,
            accounts::accounts_fetch
        ])
        .manage(ServerProcess(Mutex::new(None)))
        .setup(|app| {
            if let Some(child) = spawn_server(app) {
                if let Ok(mut guard) = app.state::<ServerProcess>().0.lock() {
                    *guard = Some(child);
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(state) = app_handle.try_state::<ServerProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                            log::info!("embedded server stopped");
                        }
                    }
                }
            }
        });
}
