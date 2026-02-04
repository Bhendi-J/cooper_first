import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authApi, usersApi, eventsApi, expensesApi, friendsApi } from "@/lib/api";

export default function ApiTestPage() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [response, setResponse] = useState<string>("");
  const [loading, setLoading] = useState(false);

  // Auth state
  const [email, setEmail] = useState("test@example.com");
  const [password, setPassword] = useState("password123");
  const [name, setName] = useState("Test User");

  // Event state
  const [eventName, setEventName] = useState("Trip to Goa");
  const [eventDescription, setEventDescription] = useState("Weekend trip");
  const [eventBudget, setEventBudget] = useState("5000");
  const [eventId, setEventId] = useState("");

  // Expense state
  const [expenseAmount, setExpenseAmount] = useState("1000");
  const [expenseDescription, setExpenseDescription] = useState("Dinner");
  const [expenseId, setExpenseId] = useState("");

  // Participant state
  const [participantUserId, setParticipantUserId] = useState("");

  // Friends state
  const [friendEmail, setFriendEmail] = useState("");
  const [friendRequestId, setFriendRequestId] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  const handleResponse = (data: unknown) => {
    setResponse(JSON.stringify(data, null, 2));
  };

  const handleError = (error: unknown) => {
    if (error && typeof error === "object" && "response" in error) {
      const axiosError = error as { response?: { data?: unknown; status?: number } };
      setResponse(JSON.stringify({
        error: true,
        status: axiosError.response?.status,
        data: axiosError.response?.data
      }, null, 2));
    } else {
      setResponse(JSON.stringify({ error: String(error) }, null, 2));
    }
  };

  const callApi = async (fn: () => Promise<unknown>) => {
    setLoading(true);
    try {
      const res = await fn();
      handleResponse((res as { data: unknown }).data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      const data = res.data;
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      }
      handleResponse(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    setLoading(true);
    try {
      const res = await authApi.register({ name, email, password });
      const data = res.data;
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      }
      handleResponse(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken("");
    setResponse(JSON.stringify({ message: "Logged out, token cleared" }, null, 2));
  };

  return (
    <div className="container mx-auto p-4 max-w-6xl">
      <h1 className="text-3xl font-bold mb-6">API Testing Dashboard</h1>

      {/* Token Display */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Current Token</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={token}
              onChange={(e) => {
                setToken(e.target.value);
                localStorage.setItem("token", e.target.value);
              }}
              placeholder="JWT Token"
              className="font-mono text-xs"
            />
            <Button variant="destructive" onClick={handleLogout}>Clear</Button>
          </div>
          {token && <p className="text-green-600 mt-2 text-sm">✓ Token is set</p>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Controls */}
        <Card>
          <CardHeader>
            <CardTitle>API Endpoints</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="auth">
              <TabsList className="grid grid-cols-5 w-full">
                <TabsTrigger value="auth">Auth</TabsTrigger>
                <TabsTrigger value="events">Events</TabsTrigger>
                <TabsTrigger value="friends">Friends</TabsTrigger>
                <TabsTrigger value="expenses">Expenses</TabsTrigger>
                <TabsTrigger value="users">Users</TabsTrigger>
              </TabsList>

              {/* Auth Tab */}
              <TabsContent value="auth" className="space-y-4">
                <div className="space-y-2">
                  <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
                  <Input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
                  <Input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={handleRegister} disabled={loading}>Register</Button>
                  <Button onClick={handleLogin} disabled={loading}>Login</Button>
                  <Button onClick={() => callApi(() => authApi.getCurrentUser())} disabled={loading}>Get Me</Button>
                </div>
              </TabsContent>

              {/* Events Tab */}
              <TabsContent value="events" className="space-y-4">
                <div className="space-y-2">
                  <Input placeholder="Event Name" value={eventName} onChange={(e) => setEventName(e.target.value)} />
                  <Input placeholder="Description" value={eventDescription} onChange={(e) => setEventDescription(e.target.value)} />
                  <Input placeholder="Event ID (for get/join/deposit)" value={eventId} onChange={(e) => setEventId(e.target.value)} />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={() => callApi(() => eventsApi.create({ name: eventName, description: eventDescription }))} disabled={loading}>
                    Create Event
                  </Button>
                  <Button onClick={() => callApi(() => eventsApi.getAll())} disabled={loading}>
                    Get My Events
                  </Button>
                  <Button onClick={() => callApi(() => eventsApi.getById(eventId))} disabled={loading || !eventId}>
                    Get Event Details
                  </Button>
                </div>
                <div className="border-t pt-4 space-y-2">
                  <h4 className="font-medium">Join & Deposit</h4>
                  <Input placeholder="Deposit Amount" type="number" value={eventBudget} onChange={(e) => setEventBudget(e.target.value)} />
                  <div className="flex gap-2">
                    <Button onClick={() => callApi(() => eventsApi.join(eventId))} disabled={loading || !eventId}>
                      Join Event
                    </Button>
                    <Button onClick={() => callApi(() => eventsApi.deposit(eventId, parseFloat(eventBudget)))} disabled={loading || !eventId}>
                      Deposit
                    </Button>
                  </div>
                </div>
                <div className="border-t pt-4 space-y-2">
                  <h4 className="font-medium">Invite Link & QR</h4>
                  <Input placeholder="Invite Code (e.g., XYZAB123)" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} />
                  <div className="flex gap-2 flex-wrap">
                    <Button onClick={() => callApi(() => eventsApi.getInviteLink(eventId))} disabled={loading || !eventId}>
                      Get Invite Link
                    </Button>
                    <Button onClick={() => callApi(() => eventsApi.getEventByCode(inviteCode))} disabled={loading || !inviteCode}>
                      Preview by Code
                    </Button>
                    <Button onClick={() => callApi(() => eventsApi.joinByCode(inviteCode))} disabled={loading || !inviteCode}>
                      Join by Code
                    </Button>
                  </div>
                </div>
              </TabsContent>

              {/* Friends Tab */}
              <TabsContent value="friends" className="space-y-4">
                <div className="space-y-2">
                  <Input placeholder="Friend's Email" value={friendEmail} onChange={(e) => setFriendEmail(e.target.value)} />
                  <Input placeholder="Request/Friend ID" value={friendRequestId} onChange={(e) => setFriendRequestId(e.target.value)} />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={() => callApi(() => friendsApi.getAll())} disabled={loading}>
                    My Friends
                  </Button>
                  <Button onClick={() => callApi(() => friendsApi.getRequests())} disabled={loading}>
                    Friend Requests
                  </Button>
                  <Button onClick={() => callApi(() => friendsApi.sendRequest({ email: friendEmail }))} disabled={loading || !friendEmail}>
                    Send Request
                  </Button>
                </div>
                <div className="border-t pt-4 space-y-2">
                  <h4 className="font-medium">Manage Requests</h4>
                  <div className="flex gap-2 flex-wrap">
                    <Button onClick={() => callApi(() => friendsApi.acceptRequest(friendRequestId))} disabled={loading || !friendRequestId} variant="default">
                      Accept Request
                    </Button>
                    <Button onClick={() => callApi(() => friendsApi.rejectRequest(friendRequestId))} disabled={loading || !friendRequestId} variant="outline">
                      Reject Request
                    </Button>
                    <Button onClick={() => callApi(() => friendsApi.remove(friendRequestId))} disabled={loading || !friendRequestId} variant="destructive">
                      Remove Friend
                    </Button>
                  </div>
                </div>
                <div className="border-t pt-4 space-y-2">
                  <h4 className="font-medium">Event Invites</h4>
                  <div className="flex gap-2 flex-wrap">
                    <Button onClick={() => callApi(() => eventsApi.getInvites())} disabled={loading}>
                      My Event Invites
                    </Button>
                    <Button onClick={() => callApi(() => eventsApi.invite(eventId, { email: friendEmail }))} disabled={loading || !eventId || !friendEmail}>
                      Invite to Event
                    </Button>
                  </div>
                </div>
              </TabsContent>

              {/* Expenses Tab */}
              <TabsContent value="expenses" className="space-y-4">
                <div className="space-y-2">
                  <Input placeholder="Event ID" value={eventId} onChange={(e) => setEventId(e.target.value)} />
                  <Input placeholder="Amount" type="number" value={expenseAmount} onChange={(e) => setExpenseAmount(e.target.value)} />
                  <Input placeholder="Description" value={expenseDescription} onChange={(e) => setExpenseDescription(e.target.value)} />
                  <Input placeholder="Expense ID (for verify)" value={expenseId} onChange={(e) => setExpenseId(e.target.value)} />
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={() => callApi(() => expensesApi.create({ event_id: eventId, amount: parseFloat(expenseAmount), description: expenseDescription }))} disabled={loading || !eventId}>
                    Create Expense
                  </Button>
                  <Button onClick={() => callApi(() => expensesApi.getByEvent(eventId))} disabled={loading || !eventId}>
                    Get Event Expenses
                  </Button>
                  <Button onClick={() => callApi(() => expensesApi.verify(expenseId))} disabled={loading || !expenseId}>
                    Verify Expense
                  </Button>
                  <Button onClick={() => callApi(() => expensesApi.getCategories())} disabled={loading}>
                    Get Categories
                  </Button>
                </div>
              </TabsContent>

              {/* Users Tab */}
              <TabsContent value="users" className="space-y-4">
                <div className="flex gap-2 flex-wrap">
                  <Button onClick={() => callApi(() => usersApi.getProfile())} disabled={loading}>
                    Get My Profile
                  </Button>
                  <Button onClick={() => callApi(() => usersApi.getAll())} disabled={loading}>
                    Get All Users
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Response Display */}
        <Card>
          <CardHeader>
            <CardTitle>Response</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-blue-600 mb-2">Loading...</p>}
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-auto max-h-[600px] text-sm font-mono">
              {response || "// Response will appear here"}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
