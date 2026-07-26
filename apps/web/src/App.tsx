import { Route, Routes } from "react-router-dom";

function FoundationPage() {
  return (
    <main className="foundation">
      <section aria-labelledby="product-title">
        <p className="eyebrow">Machine learning operations</p>
        <h1 id="product-title">RunScope</h1>
        <p>
          The control plane is ready. Authentication and experiment workflows are
          added in the next vertical slices.
        </p>
      </section>
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="*" element={<FoundationPage />} />
    </Routes>
  );
}
