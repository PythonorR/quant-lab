import { PageTitle } from "@/components/ui";
import ListsView from "./ListsView";

export default function ListsPage() {
  return (
    <>
      <PageTitle sub="Groups of stocks a strategy can pick from.">Stock lists</PageTitle>
      <ListsView />
    </>
  );
}
