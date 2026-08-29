import { team } from "@/lib/team";

export default function TeamCredits() {
  return (
    <section className="team" aria-labelledby="team-heading">
      <h2 id="team-heading" className="team-heading">
        Team {team.name} · {team.event}
      </h2>
      <dl className="team-list">
        <div>
          <dt>Leader</dt>
          <dd>{team.leader.name}</dd>
          <dd className="team-id">{team.leader.id}</dd>
        </div>
        {team.members.map((member) => (
          <div key={member.id}>
            <dt>Member</dt>
            <dd>{member.name}</dd>
            <dd className="team-id">{member.id}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
