const cards = [
  ["ACTIVE PROJECTS", "—"],
  ["OPEN TASKS", "—"],
  ["HIGH RISK", "—"],
  ["AI REVIEW", "—"],
];

export default function Home() {
  return (
    <main>
      <div className="brand">AI PMO / COMMAND CENTER</div>
      <h1>MIRANOAH</h1>
      <p className="tagline">すべてを見渡し、一つも取りこぼさない。Slackから仕事を理解し、組織全体のタスク・期限・Todo・リスクを統合する。</p>
      <div className="grid">
        {cards.map(([label, value]) => (
          <div className="card" key={label}><span>{label}</span><strong>{value}</strong><div className="status">Backend connection pending</div></div>
        ))}
      </div>
    </main>
  );
}
