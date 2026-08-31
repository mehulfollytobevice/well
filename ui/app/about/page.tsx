export default function AboutPage() {
  return (
    <main className="shell">
      <header>
        <div>
          <h1>Data & attribution</h1>
          <p>Public Utah FORGE / DOE GDR datasets (CC-BY 4.0)</p>
        </div>
        <a href="/">Back</a>
      </header>
      <section className="panel">
        <p>
          WellGround indexes public DOE Geothermal Data Repository submissions for wells
          16A(78)-32 and 16B(78)-32. Full provenance lives in the repository at
          {" "}
          <code>data/PROVENANCE.md</code>.
        </p>
        <ul>
          <li>
            Extended circulation time series —{" "}
            <a href="https://doi.org/10.15121/2475065">10.15121/2475065</a>
          </li>
          <li>
            Circulation daily reports —{" "}
            <a href="https://doi.org/10.15121/2455019">10.15121/2455019</a>
          </li>
          <li>
            Injection / production test reports —{" "}
            <a href="https://doi.org/10.15121/2473673">10.15121/2473673</a>
          </li>
        </ul>
      </section>
    </main>
  );
}
