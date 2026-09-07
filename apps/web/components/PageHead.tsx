export function PageHead({ eyebrow, title, lede }: { eyebrow: string; title: string; lede?: string }) {
  return (
    <div className="page-head">
      <p className="eyebrow" style={{ margin: 0 }}>{eyebrow}</p>
      <h1 className="h2">{title}</h1>
      {lede && <p className="lede">{lede}</p>}
    </div>
  );
}
