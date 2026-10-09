import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Protected from "./components/Protected";
import Assistant from "./pages/Assistant";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Models from "./pages/Models";
import Upload from "./pages/Upload";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected />}>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="models" element={<Models />} />
          <Route element={<Protected roles={["admin", "officer", "analyst"]} />}>
            <Route path="assistant" element={<Assistant />} />
          </Route>
          <Route element={<Protected roles={["admin", "officer"]} />}>
            <Route path="upload" element={<Upload />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
