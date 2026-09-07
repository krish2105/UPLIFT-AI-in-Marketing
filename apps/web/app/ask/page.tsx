import { PageHead } from "@/components/PageHead";
import { AskView } from "@/components/views/AskView";

export default function AskPage() {
  return (
    <div className="page">
      <PageHead
        eyebrow="System"
        title="Ask"
        lede="Questions answered out of the project's own corpus, with the source attached. There is no generation step, so there is nothing that could invent an answer."
      />
      <AskView />
    </div>
  );
}
