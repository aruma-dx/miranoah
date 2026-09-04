import AIReviewPage from "../components/AIReviewPage";


export const dynamic =
  "force-dynamic";


export default function Page() {
  const apiBaseUrl =
    process.env.API_BASE_URL
    ?? "";

  return (
    <AIReviewPage
      apiBaseUrl={
        apiBaseUrl
      }
    />
  );
}
