package main

func add(a int, b int) int {
    return a + b
}

func (s *Server) Name(prefix string) string {
    return prefix
}
