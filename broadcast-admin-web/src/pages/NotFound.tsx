import { Link } from "react-router-dom";

export const NotFoundPage = () => (
  <section className="page">
    <header>
      <h1>404</h1>
      <p>The requested page does not exist.</p>
    </header>
    <Link to="/" className="primary-link">
      Back to dashboard
    </Link>
  </section>
);

