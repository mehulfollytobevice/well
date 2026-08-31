import { AskPanel } from "@/components/AskPanel";

export default function HomePage() {
  return (
    <main className="shell">
      <header>
        <div>
          <h1>WellGround</h1>
          <p>Grounded agentic ops Q&A for Utah FORGE</p>
        </div>
        <a href="/about">Data & attribution</a>
      </header>
      <AskPanel />
      <footer>
        Answers cite retrieved SQL rows and report passages. Not engineering advice.
      </footer>
    </main>
  );
}
