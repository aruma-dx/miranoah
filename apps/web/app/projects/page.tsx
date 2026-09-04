import {
  ProjectsListPage,
} from "../components/EntityListPages";

export const dynamic =
  "force-dynamic";

export default function Page() {
  const apiBaseUrl =
    process.env.API_BASE_URL ?? "";

  return (
    <ProjectsListPage
      apiBaseUrl={apiBaseUrl}
    />
  );
}
