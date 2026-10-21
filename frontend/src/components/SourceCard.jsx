import "./SourceCard.css";

/**
 * The citation footer under a confident answer (Section 21/22). When the
 * record's true source is "the college's own official site" rather than
 * one fixed URL — the backend already resolved this and sends url: null
 * — we say so in plain language instead of rendering a dead link.
 */
export default function SourceCard({ source, verificationDate, requiresVerification }) {
  if (!source) return null;

  return (
    <div className="source-line">
      <span className="source-line__mark" aria-hidden="true" />
      {source.url ? (
        <a href={source.url} target="_blank" rel="noreferrer">
          {source.name}
        </a>
      ) : (
        <span>{source.name} — check the college's current page directly</span>
      )}
      {verificationDate && <span className="source-line__date">· checked {verificationDate}</span>}
      {requiresVerification && (
        <span className="source-line__badge">may change by cycle</span>
      )}
    </div>
  );
}
