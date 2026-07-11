import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  { ignores: [".next-e2e/**", "test-results/**", "playwright-report/**"] },
  ...nextVitals
];

export default config;
