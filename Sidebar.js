import React, { useState } from "react";
import { Link } from "react-router-dom";
import { FaHome, FaHistory, FaSignOutAlt, FaBars } from "react-icons/fa";
import "./Sidebar.css";

function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <button className="toggle-btn" onClick={() => setCollapsed(!collapsed)}>
        <FaBars />
      </button>
      <ul>
        <li>
          <Link to="/home">
            <FaHome /> <span className="link-text">Home</span>
          </Link>
        </li>
        <li>
          <Link to="/history">
            <FaHistory /> <span className="link-text">History</span>
          </Link>
        </li>
        <li>
          <Link to="/login" onClick={() => localStorage.removeItem("token")}>
            <FaSignOutAlt /> <span className="link-text">Logout</span>
          </Link>
        </li>
      </ul>
    </div>
  );
}

export default Sidebar;
