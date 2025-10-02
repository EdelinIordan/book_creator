import styles from "./StructureTimeline.module.css";

type Iteration = {
  id: string;
  role: "proposal" | "critique" | "improvement" | "summary";
  title: string;
  content: string;
  timestamp: string;
};

export function StructureTimeline({ iterations }: { iterations: Iteration[] }) {
  return (
    <div className={styles.timeline}>
      {iterations.map((iteration) => (
        <article key={iteration.id} className={styles.card}>
          <header>
            <span className={styles.role}>{iteration.role.toUpperCase()}</span>
            <time>{new Date(iteration.timestamp).toLocaleTimeString()}</time>
          </header>
          <h3>{iteration.title}</h3>
          <p>{iteration.content}</p>
        </article>
      ))}
    </div>
  );
}
