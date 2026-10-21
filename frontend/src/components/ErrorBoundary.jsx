import { Component } from "react";
import "./ErrorBoundary.css";

/**
 * Section 35's error handling only covers API/network failures (handled
 * inside useChat). A JS runtime error anywhere in the render tree is a
 * different failure mode entirely — without this boundary it would
 * produce a blank white screen with no way to recover. React error
 * boundaries must be class components; this is the one class component
 * in an otherwise all-function-component codebase for exactly that
 * reason.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Section 43: log the real error server-side-equivalent (browser
    // console here); never show the stack trace in the UI itself.
    console.error("CollegePath AI crashed:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="crash-screen">
          <p className="crash-screen__title">Something went wrong.</p>
          <p className="crash-screen__body">
            Please reload the page. If this keeps happening, the issue has been logged.
          </p>
          <button type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
