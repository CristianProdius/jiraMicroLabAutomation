import packageJson from "../../package.json";

const currentYear = new Date().getFullYear();

export const APP_CONFIG = {
  name: "Jira Microlab Automation",
  subtitle: "In collaboration with Prodius Enterprise",
  version: packageJson.version,
  copyright: `© ${currentYear}, Prodius Enterprise.`,
  meta: {
    title: "Jira Microlab Automation - Issue Feedback Dashboard",
    description:
      "Jira Microlab Automation is a Jira issue analysis and feedback platform that helps teams improve issue quality through automated rubric scoring and AI-powered suggestions. In collaboration with Prodius Enterprise.",
  },
};
