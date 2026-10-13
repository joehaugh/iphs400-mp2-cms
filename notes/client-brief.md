# Client brief: Jesuit Schools Network

**Who runs the site, and how comfortable are they with computers?**
Jennifer LaMaster, director of the Jesuit Schools Network, oversees it. She heads a
big organization and has a tech team under her, so she supervises and does not
write content day to day. Each member high school has its own editor, usually the
head of alumni relations (Fordham Prep's would be JP Feighery). They write
blog-style posts about their own school and decide which alumni may join.

**Who reads it, and what are they usually trying to find?**
Alumni of the Jesuit schools. They want news from their own school and from the
other schools, and a way to reach alumni of other schools who share a Jesuit
education and similar interests.

**What is broken about how they do it now?**
Content is scattered across social media accounts or buried on each school's news
page. There is no single place, so alumni connect with their own classmates but
not with the wider network.

**What would make them say "this is better"?**
One place where each school's posts and the alumni network live together, so the
network connects people across schools and not only within one.

**What must not happen?**
- An editor at one school must never delete another school's pages.
- An editor must not approve or deny alumni for any school but their own. Once a
  Fordham Prep alumnus is approved by Fordham Prep, a school like Xavier High
  School (New York) must still grant that person access to see its posts and
  alumni network.
- Contact details are private by default and shared only as the alumnus chooses
  (see below).

**Alumni privacy (client's wish):** each alumnus can set phone, email and occupation
to private, visible only to their own school, or visible to all schools in the
network.

---

## Scope notes (for the grill, not the client's words)

The client's reality is bigger than the seven required capabilities. Open
questions to settle in `/grill-with-docs`:

- **Alumni accounts, approval and per-field privacy** need logins for readers. The
  public site is static HTML, so there are no reader logins, and the admin console
  never goes on the public internet. These are likely out of scope or reduced to
  something the static site can do.
- **Per-school editors** with edit rights limited to their own school need a
  school-ownership rule on posts and pages. The required roles are only admin and
  editor, so "editor of one school" must be an editor whose permissions are scoped
  by school.
- Decided in-scope version: Jennifer is the admin, school editors are editors
  scoped to their school, and the public site shows each school's published posts
  and pages.
- Stretch, only after the CMS works: a non-functional mockup of the social-network
  version (alumni directory, privacy settings). Kept outside `site/`, made-up data.
