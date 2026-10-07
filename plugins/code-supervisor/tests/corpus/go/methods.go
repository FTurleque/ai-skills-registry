package main

type Stack[T any] struct{ items []T }

func (s *Stack[T]) Push(item T) {
    s.items = append(s.items, item)
}

func (Stack[T]) Size() int {
    return 0
}

func (s Server) Handle(request string, retries int) (string, error) {
    if retries > 3 {
        return "", nil
    }
    return request, nil
}

func helper(value int) int {
    return value * 2
}
