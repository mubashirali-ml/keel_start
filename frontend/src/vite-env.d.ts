/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" in recorded-run builds: include the `/design` gallery (launch_agents/devtools/ui_run.py). */
  readonly VITE_DESIGN_GALLERY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
