import React from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, ArrowLeft, Home, Users, Settings, FileText, TrendingUp, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import DashboardRenderer from '@/components/DashboardRenderer';

const DemoPage = () => {
    // Hard-coded demo data with all chart types and components
    const demoData = {
        title: "TransIQ Demo Dashboard",
        description: "Sample analytics dashboard showcasing TransIQ's capabilities with comprehensive business intelligence",
        kpis: [
            {
                id: "revenue",
                title: "Total Revenue",
                value: 125000,
                unit: "$",
                change: "+12.5%",
                changeType: "positive" as const,
                icon: "dollar",
                color: "#06b6d4"
            },
            {
                id: "users",
                title: "Active Users",
                value: 78920,
                unit: "",
                change: "+8.2%",
                changeType: "positive" as const,
                icon: "users",
                color: "#10b981"
            },
            {
                id: "efficiency",
                title: "Efficiency Score",
                value: 89.4,
                unit: "%",
                change: "+2.1%",
                changeType: "positive" as const,
                icon: "activity",
                color: "#f59e0b"
            },
            {
                id: "orders",
                title: "Orders Processed",
                value: 65300,
                unit: "",
                change: "-3.4%",
                changeType: "negative" as const,
                icon: "chart",
                color: "#ef4444"
            }
        ],
        charts: [
            {
                id: "sales-trend",
                type: "AreaChart" as const,
                title: "Sales Performance Trend",
                subtitle: "Monthly sales data over the last 12 months",
                size: "half" as const,
                chartConfig: {
                    xAxis: {
                        dataKey: "month",
                        label: "Month",
                        type: "category" as const
                    },
                    yAxis: {
                        label: "Sales ($)",
                        domain: [0, 150000] as [number, number]
                    },
                    series: [
                        {
                            dataKey: "sales",
                            name: "Sales",
                            type: "area" as const,
                            color: "#06b6d4",
                            fill: "#06b6d4",
                            stroke: "#06b6d4"
                        },
                        {
                            dataKey: "target",
                            name: "Target",
                            type: "line" as const,
                            color: "#10b981",
                            stroke: "#10b981"
                        }
                    ]
                },
                data: [
                    { month: "Jan", sales: 85000, target: 80000 },
                    { month: "Feb", sales: 92000, target: 85000 },
                    { month: "Mar", sales: 78000, target: 90000 },
                    { month: "Apr", sales: 105000, target: 95000 },
                    { month: "May", sales: 118000, target: 100000 },
                    { month: "Jun", sales: 125000, target: 110000 },
                    { month: "Jul", sales: 135000, target: 115000 },
                    { month: "Aug", sales: 142000, target: 120000 },
                    { month: "Sep", sales: 138000, target: 125000 },
                    { month: "Oct", sales: 145000, target: 130000 },
                    { month: "Nov", sales: 152000, target: 135000 },
                    { month: "Dec", sales: 148000, target: 140000 }
                ]
            },
            {
                id: "customer-satisfaction",
                type: "PieChart" as const,
                title: "Customer Satisfaction",
                subtitle: "Distribution of customer satisfaction ratings",
                size: "half" as const,
                chartConfig: {
                    series: [
                        {
                            dataKey: "value",
                            name: "Satisfaction",
                            type: "bar" as const
                        }
                    ]
                },
                data: [
                    { category: "Excellent", value: 45, color: "#10b981" },
                    { category: "Good", value: 30, color: "#06b6d4" },
                    { category: "Average", value: 18, color: "#f59e0b" },
                    { category: "Poor", value: 7, color: "#ef4444" }
                ]
            },
            {
                id: "department-performance",
                type: "BarChart" as const,
                title: "Department Performance",
                subtitle: "Performance metrics by department",
                size: "half" as const,
                chartConfig: {
                    xAxis: {
                        dataKey: "department",
                        label: "Department",
                        type: "category" as const
                    },
                    yAxis: {
                        label: "Score",
                        domain: [0, 100] as [number, number]
                    },
                    series: [
                        {
                            dataKey: "performance",
                            name: "Performance Score",
                            type: "bar" as const,
                            color: "#06b6d4",
                            fill: "#06b6d4"
                        },
                        {
                            dataKey: "efficiency",
                            name: "Efficiency Score",
                            type: "bar" as const,
                            color: "#10b981",
                            fill: "#10b981"
                        }
                    ]
                },
                data: [
                    { department: "Sales", performance: 92, efficiency: 88 },
                    { department: "Marketing", performance: 85, efficiency: 90 },
                    { department: "Operations", performance: 78, efficiency: 85 },
                    { department: "Customer Service", performance: 95, efficiency: 92 },
                    { department: "IT", performance: 88, efficiency: 94 },
                    { department: "HR", performance: 82, efficiency: 86 }
                ]
            },
            {
                id: "real-time-activity",
                type: "LineChart" as const,
                title: "Real-time Activity",
                subtitle: "Live activity monitoring over the past 24 hours",
                size: "half" as const,
                chartConfig: {
                    xAxis: {
                        dataKey: "time",
                        label: "Time",
                        type: "category" as const
                    },
                    yAxis: {
                        label: "Activity",
                        domain: [0, 100] as [number, number]
                    },
                    series: [
                        {
                            dataKey: "activity",
                            name: "Activity Level",
                            type: "line" as const,
                            color: "#f59e0b",
                            stroke: "#f59e0b"
                        }
                    ]
                },
                data: [
                    { time: "00:00", activity: 15 },
                    { time: "04:00", activity: 8 },
                    { time: "08:00", activity: 45 },
                    { time: "12:00", activity: 78 },
                    { time: "16:00", activity: 92 },
                    { time: "20:00", activity: 65 },
                    { time: "24:00", activity: 25 }
                ]
            },
            {
                id: "quarterly-comparison",
                type: "ComposedChart" as const,
                title: "Quarterly Sales by Region",
                subtitle: "Revenue and growth comparison across regions",
                size: "full" as const,
                chartConfig: {
                    xAxis: {
                        dataKey: "region",
                        label: "Region",
                        type: "category" as const
                    },
                    yAxis: {
                        label: "Revenue ($)",
                        domain: [0, 200000] as [number, number]
                    },
                    composedComponents: [
                        {
                            type: "Bar" as const,
                            dataKey: "q1",
                            name: "Q1 Revenue",
                            color: "#06b6d4",
                            fill: "#06b6d4"
                        },
                        {
                            type: "Bar" as const,
                            dataKey: "q2",
                            name: "Q2 Revenue",
                            color: "#10b981",
                            fill: "#10b981"
                        },
                        {
                            type: "Line" as const,
                            dataKey: "growth",
                            name: "Growth %",
                            color: "#f59e0b",
                            stroke: "#f59e0b"
                        }
                    ]
                },
                data: [
                    { region: "North America", q1: 150000, q2: 165000, growth: 10 },
                    { region: "Europe", q1: 120000, q2: 135000, growth: 12.5 },
                    { region: "Asia Pacific", q1: 95000, q2: 118000, growth: 24.2 },
                    { region: "Latin America", q1: 75000, q2: 82000, growth: 9.3 },
                    { region: "Middle East", q1: 60000, q2: 72000, growth: 20 }
                ]
            },
            {
                id: "revenue-breakdown",
                type: "RadialBarChart" as const,
                title: "Revenue by Category",
                subtitle: "Breakdown of revenue streams",
                size: "third" as const,
                chartConfig: {
                    series: [
                        {
                            dataKey: "value",
                            name: "Revenue",
                            type: "bar" as const
                        }
                    ]
                },
                data: [
                    { category: "Products", value: 65, color: "#06b6d4" },
                    { category: "Services", value: 45, color: "#10b981" },
                    { category: "Subscriptions", value: 80, color: "#f59e0b" },
                    { category: "Consulting", value: 35, color: "#8b5cf6" }
                ]
            }
        ],
        tables: [
            {
                id: "top-customers",
                title: "Top Customers by Revenue",
                columns: [
                    { key: "company", label: "Company", type: "string" },
                    { key: "revenue", label: "Revenue", type: "currency", format: "$" },
                    { key: "growth", label: "Growth", type: "percentage" },
                    { key: "status", label: "Status", type: "string" }
                ],
                data: [
                    { company: "Acme Corp", revenue: 125000, growth: 15.2, status: "Active" },
                    { company: "TechnoSoft", revenue: 98000, growth: 8.7, status: "Active" },
                    { company: "Global Industries", revenue: 87000, growth: -2.1, status: "At Risk" },
                    { company: "StartupXYZ", revenue: 76000, growth: 22.5, status: "Growing" },
                    { company: "Enterprise Ltd", revenue: 65000, growth: 5.8, status: "Stable" }
                ],
                pagination: true,
                sortable: true
            }
        ],
        optimizationSuggestions: [
            {
                id: "cost-optimization",
                title: "Server Infrastructure Optimization",
                category: "cost" as const,
                impact: "high" as const,
                savings: {
                    value: 25000,
                    unit: "$",
                    percentage: "18%",
                    timeframe: "annually"
                },
                description: "Migrate to cloud infrastructure to reduce server costs and improve scalability. Current on-premise setup is underutilized during off-peak hours.",
                implementation: "Gradual migration over 3 months with minimal downtime",
                metrics: ["Cost per transaction", "Server utilization", "Response time"],
                priority: "high" as const,
                confidence: "high" as const,
                tags: ["Cloud Migration", "Cost Reduction", "Infrastructure"],
                actionable: true,
                color: "#10b981"
            },
            {
                id: "inventory-optimization",
                title: "Inventory Management Enhancement",
                category: "efficiency" as const,
                impact: "medium" as const,
                savings: {
                    value: 15000,
                    unit: "$",
                    percentage: "12%",
                    timeframe: "quarterly"
                },
                description: "Implement predictive analytics for inventory management to reduce overstocking and stockouts. Current inventory turnover is below industry average.",
                implementation: "Deploy ML-based demand forecasting system",
                metrics: ["Inventory turnover", "Stock accuracy", "Demand forecast accuracy"],
                priority: "medium" as const,
                confidence: "high" as const,
                tags: ["Inventory", "Predictive Analytics", "Supply Chain"],
                actionable: true,
                color: "#06b6d4"
            },
            {
                id: "customer-retention",
                title: "Customer Retention Program",
                category: "performance" as const,
                impact: "high" as const,
                savings: {
                    value: 45000,
                    unit: "$",
                    percentage: "25%",
                    timeframe: "annually"
                },
                description: "Implement targeted retention campaigns for at-risk customers. Analysis shows 15% of customers are at risk of churning within 90 days.",
                implementation: "Automated email campaigns with personalized offers",
                metrics: ["Customer retention rate", "Churn prediction accuracy", "Campaign ROI"],
                priority: "high" as const,
                confidence: "medium" as const,
                tags: ["Customer Retention", "Marketing Automation", "Churn Prevention"],
                actionable: true,
                color: "#f59e0b"
            },
            {
                id: "process-automation",
                title: "Manual Process Automation",
                category: "efficiency" as const,
                impact: "medium" as const,
                savings: {
                    value: 18000,
                    unit: "$",
                    percentage: "22%",
                    timeframe: "annually"
                },
                description: "Automate manual data entry processes that currently consume 40+ hours per week. Implement RPA for routine administrative tasks.",
                implementation: "Deploy RPA bots for repetitive tasks",
                metrics: ["Process completion time", "Error rate", "Employee productivity"],
                priority: "medium" as const,
                confidence: "high" as const,
                tags: ["Automation", "RPA", "Process Improvement"],
                actionable: true,
                color: "#8b5cf6"
            }
        ],
        insights: {
            summary: "Strong performance across key metrics with significant growth opportunities identified in customer retention and operational efficiency.",
            trends: [
                "Revenue growth accelerating with 12.5% increase this quarter",
                "Customer satisfaction ratings improved by 8% over last quarter",
                "Operational efficiency gains of 15% through recent optimizations",
                "Market expansion opportunities in Asia Pacific region showing 24% growth"
            ],
            alerts: [
                {
                    type: "warning" as const,
                    message: "Customer churn rate increased to 8.2% - above industry average",
                    severity: "high" as const,
                    action: "Implement retention strategies immediately"
                },
                {
                    type: "success" as const,
                    message: "Q2 revenue targets exceeded by 15%",
                    severity: "medium" as const,
                    action: "Review and adjust Q3 targets upward"
                },
                {
                    type: "info" as const,
                    message: "New market opportunities identified in emerging markets",
                    severity: "low" as const,
                    action: "Conduct market analysis for expansion planning"
                }
            ],
            recommendations: [
                "Focus on customer retention initiatives to reduce churn",
                "Invest in operational automation to improve efficiency",
                "Expand into high-growth Asia Pacific market",
                "Optimize inventory management using predictive analytics"
            ]
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex">
            {/* Sidebar */}
            <div className="w-64 bg-slate-900/50 backdrop-blur-sm border-r border-slate-700/50 flex flex-col">
                {/* Logo */}
                <div className="p-6 border-b border-slate-700/50">
                    <Link to="/" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
                        <div className="w-8 h-8 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-lg flex items-center justify-center">
                            <BarChart3 className="h-4 w-4 text-white" />
                        </div>
                        <span className="text-xl font-bold text-white">TransIQ</span>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-4 py-6 space-y-2">
                    <Link to="/" className="flex items-center space-x-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/50 hover:text-white transition-colors">
                        <Home className="h-4 w-4" />
                        <span>Home</span>
                    </Link>
                    <Link to="/upload" className="flex items-center space-x-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/50 hover:text-white transition-colors">
                        <FileText className="h-4 w-4" />
                        <span>Upload Data</span>
                    </Link>
                    <div className="flex items-center space-x-3 px-3 py-2 rounded-lg text-cyan-400 bg-slate-800/50">
                        <TrendingUp className="h-4 w-4" />
                        <span>Demo Dashboard</span>
                    </div>
                    <div className="flex items-center space-x-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/50 hover:text-white transition-colors">
                        <Users className="h-4 w-4" />
                        <span>Profile</span>
                    </div>
                    <div className="flex items-center space-x-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/50 hover:text-white transition-colors">
                        <Settings className="h-4 w-4" />
                        <span>Settings</span>
                    </div>
                </nav>

                {/* Back to Home */}
                <div className="p-4 border-t border-slate-700/50">
                    <Link to="/">
                        <Button className="w-full bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Home
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Top Navigation */}
                <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-700/50 px-6 py-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                            <h1 className="text-2xl font-bold text-white">Demo Dashboard</h1>
                            <div className="bg-cyan-500/20 text-cyan-400 px-3 py-1 rounded-full text-sm font-medium">
                                Sample Data
                            </div>
                        </div>
                    </div>
                </div>

                {/* Dashboard Content */}
                <div className="flex-1 overflow-auto">
                    <DashboardRenderer dashboardData={demoData} />
                </div>
            </div>
        </div>
    );
};

export default DemoPage;
