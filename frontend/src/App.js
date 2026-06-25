import React, { useState } from "react";
import "./App.css";
import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import About from "./components/About";
import Interviews from "./components/Interviews";
import Episodes from "./components/Episodes";
import Predictions from "./components/Predictions";
import Hosts from "./components/Hosts";
import Press from "./components/Press";
import SocialSection from "./components/SocialSection";
import Footer from "./components/Footer";
import VideoModal from "./components/VideoModal";

function App() {
  const [video, setVideo] = useState(null);

  return (
    <div className="App">
      <Navbar />
      <main>
        <Hero />
        <About />
        <Interviews onPlay={setVideo} />
        <Episodes onPlay={setVideo} />
        <Predictions />
        <Hosts />
        <Press />
        <SocialSection />
      </main>
      <Footer />
      <VideoModal video={video} onClose={() => setVideo(null)} />
    </div>
  );
}

export default App;
