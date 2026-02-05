import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DebtNotificationProvider } from "@/components/DebtNotificationProvider";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import EventCreate from "./pages/EventCreate";
import EventDetail from "./pages/EventDetail";
import ExpenseAdd from "./pages/ExpenseAdd";
import JoinEvent from "./pages/JoinEvent";
import Payment from "./pages/Payment";
import PaymentCallback from "./pages/PaymentCallback";
import PaymentProcessing from "./pages/PaymentProcessing";
import SettleUp from "./pages/SettleUp";
import PaymentConfirm from "./pages/PaymentConfirm";
import Wallet from "./pages/Wallet";
import Wellness from "./pages/Wellness";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <DebtNotificationProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/events/create" element={<EventCreate />} />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/events/:id/expense" element={<ExpenseAdd />} />
            <Route path="/join/:code" element={<JoinEvent />} />
            <Route path="/payment" element={<Payment />} />
            <Route path="/payment/callback" element={<PaymentCallback />} />
            <Route path="/payment/processing" element={<PaymentProcessing />} />
            <Route path="/events/:id/settle" element={<SettleUp />} />
            <Route path="/payment/confirm/:intentId" element={<PaymentConfirm />} />
            <Route path="/wallet" element={<Wallet />} />
            <Route path="/wellness" element={<Wellness />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </DebtNotificationProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
