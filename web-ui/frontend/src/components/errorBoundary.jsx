import React, { Component } from 'react';

class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        // You can also log error reports to the server
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({
            hasError: true,
            error: error,
            errorInfo: errorInfo
        });
    }

    render() {
        if (this.state.hasError) {
            // You can render any custom fallback UI
            return (
                <div />
            );
        }

        // console.error("ErrorBoundary caught an error:", this.state.error, this.state.errorInfo);

        return this.props.children;
    }
}

export default ErrorBoundary;