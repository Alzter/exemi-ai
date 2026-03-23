declare module "*.css?inline" {
  const css: string;
  export default css;
}

interface ImportMetaEnv {
  readonly VITE_CANVAS_TOKEN_EXPIRY_DAYS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
