import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const features = [
  {
    emoji: "🔐",
    title: "Authentication",
    description: "JWT-based auth with secure session management out of the box.",
  },
  {
    emoji: "🎨",
    title: "UI Components",
    description: "Beautiful, accessible components built with Tailwind CSS.",
  },
  {
    emoji: "⚡",
    title: "API Ready",
    description: "Flask backend with RESTful endpoints ready to extend.",
  },
  {
    emoji: "🗄️",
    title: "MongoDB",
    description: "NoSQL database integration with Mongoose ODM.",
  },
  {
    emoji: "🔄",
    title: "Hot Reload",
    description: "Instant feedback with Vite's lightning-fast HMR.",
  },
  {
    emoji: "📱",
    title: "Responsive",
    description: "Mobile-first design that looks great on any device.",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: "easeOut" as const,
    },
  },
};

export default function HomePage() {
  return (
    <div className="min-h-screen mesh-gradient">
      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto text-center">
          {/* Floating Rocket */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              type: "spring",
              stiffness: 200,
              damping: 15,
              delay: 0.2,
            }}
            className="mb-8"
          >
            <span className="text-8xl sm:text-9xl inline-block animate-float">
              🚀
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6"
          >
            <span className="gradient-text-hero">Build Fast.</span>
            <br />
            <span className="gradient-text-hero">Win Big.</span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-xl sm:text-2xl text-muted-foreground max-w-2xl mx-auto mb-10"
          >
            The ultimate full-stack starter kit for hackathons.{" "}
            <span className="text-foreground font-medium">React + Flask + MongoDB</span>{" "}
            boilerplate to launch your next winning project.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              to="/register"
              className="group flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold bg-gradient-primary text-primary-foreground glow-button hover:shadow-glow-lg transition-all duration-300 press-effect"
            >
              Get Started Free
              <ArrowRight
                size={20}
                className="group-hover:translate-x-1 transition-transform"
              />
            </Link>
            <Link
              to="/login"
              className="px-8 py-4 rounded-xl text-lg font-semibold border-2 border-border hover:border-primary/50 hover:bg-secondary/50 transition-all duration-300"
            >
              Login
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="pb-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                variants={itemVariants}
                className="feature-card group cursor-default"
              >
                <span className="text-4xl mb-4 block group-hover:scale-110 transition-transform duration-300">
                  {feature.emoji}
                </span>
                <h3 className="text-xl font-bold mb-2 text-foreground">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="pb-24 px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="max-w-4xl mx-auto text-center glass-card p-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4 gradient-text-hero">
            Ready to hack?
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Join thousands of developers building amazing projects with HackStarter.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold bg-gradient-primary text-primary-foreground glow-button hover:shadow-glow-lg transition-all duration-300 press-effect"
          >
            Start Building Now
            <ArrowRight size={20} />
          </Link>
        </motion.div>
      </section>
    </div>
  );
}
